"""



                                                    NOTES:
                    Monarch_API_v2 acts as the main communication layer between
                    the Monarch mobile app, the orchestrator, and all active trading agents.

                    It tracks live agent data, total profit, trade history, logs,
                    pause/resume commands, emergency stops, and chart data for
                    daily, monthly, and yearly performance.

                    KEY FEATURES:
                     - Mobile app API backend
                     - Agent status tracking
                     - Total profit tracking
                     - Daily, monthly, and yearly chart data
                     - Trade history logging
                     - Pause and resume controls
                     - Emergency stop control
                     - Orchestrator communication
                     - Add-agent request system
                     - Agent data loading and saving support


"""

from fastapi import FastAPI
import uvicorn
from typing import Dict
import os
import threading
from datetime import datetime
import time
import json
from pathlib import Path
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import pandas_market_calendars as mcal

RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"  # purple-ish
CYAN    = "\033[96m"
WHITE   = "\033[97m"

# Extras that are often useful
ORANGE  = "\033[38;5;208m"  # 256-color mode
PINK    = "\033[38;5;213m"
PURPLE  = "\033[38;5;129m"
GRAY    = "\033[90m"

# Styles (optional but handy)
BOLD    = "\033[1m"
DIM     = "\033[2m"
UNDERLINE = "\033[4m"

RESET   = "\033[0m"

def print_c(text, color):
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"  # purple-ish
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    # Extras that are often useful
    ORANGE  = "\033[38;5;208m"  # 256-color mode
    PINK    = "\033[38;5;213m"
    PURPLE  = "\033[38;5;129m"
    GRAY    = "\033[90m"

    # Styles (optional but handy)
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    UNDERLINE = "\033[4m"

    RESET   = "\033[0m"
    if color.lower() == "red":
        print(f"{RED}{text}{RESET}")
    elif color.lower() == "green":
        print(f"{GREEN}{text}{RESET}")
    elif color.lower() == "yellow":
        print(f"{YELLOW}{text}{RESET}")
    elif color.lower() == "blue":
        print(f"{BLUE}{text}{RESET}")
    elif color.lower() == "magenta":
        print(f"{MAGENTA}{text}{RESET}")
    elif color.lower() == "cyan":
        print(f"{CYAN}{text}{RESET}")
    elif color.lower() == "white":
        print(f"{WHITE}{text}{RESET}")
    elif color.lower() == "orange":
        print(f"{ORANGE}{text}{RESET}")
    elif color.lower() == "pink":
        print(f"{PINK}{text}{RESET}")
    elif color.lower() == "purple":
        print(f"{PURPLE}{text}{RESET}")
    elif color.lower() == "gray":
        print(f"{GRAY}{text}{RESET}")
    else:
        print(text)


app = FastAPI()


# Current day/month/year Trades
CDT = []
CMT = []
CYT = []

hour = 5
minute = 2
timeZone = "America/Chicago"

agents = {}
months_profit = 0  #this is where the total month's profit is stored

agents_to_add = {}


logs = []
pause_status = False
E_stop_status = False

agents_to_delete = []


# ---------------------- JSON state saving ----------------------

DATA_DIR = Path(os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "monarch_state.json"

state_lock = threading.Lock()


def default_state():
    return {
        "CDT": [],
        "CMT": [],
        "CYT": [],
        "agents": {},
        "months_profit": 0.0,
        "pause_status": False,
        "E_stop_status": False,
        "hour": 5,
        "minute": 2,
        "timeZone": "America/Chicago"
    }


def save_state():
    global CDT, CMT, CYT, agents, months_profit, agents_to_add, logs
    global OC_status, pause_status, E_stop_status, hour, minute, timeZone

    state = {
        "CDT": CDT,
        "CMT": CMT,
        "CYT": CYT,
        "agents": agents,
        "months_profit": months_profit,
        "pause_status": pause_status,
        "E_stop_status": E_stop_status,
        "hour": hour,
        "minute": minute,
        "timeZone": timeZone
    }

    with state_lock:
        temp_file = STATE_FILE.with_suffix(".tmp")

        with open(temp_file, "w") as f:
            json.dump(state, f, indent=4)

        temp_file.replace(STATE_FILE)


def load_state():
    global CDT, CMT, CYT, agents, months_profit, agents_to_add, logs
    global OC_status, pause_status, E_stop_status, hour, minute, timeZone

    if not STATE_FILE.exists():
        with open(STATE_FILE, "w") as f:
            json.dump(default_state(), f, indent=4)

    with state_lock:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

    CDT = state.get("CDT", [])
    CMT = state.get("CMT", [])
    CYT = state.get("CYT", [])
    agents = state.get("agents", {})
    months_profit = state.get("months_profit", 0.0)
    pause_status = state.get("pause_status", False)
    E_stop_status = state.get("E_stop_status", False)
    hour = state.get("hour", 5)
    minute = state.get("minute", 2)
    timeZone = state.get("timeZone", "America/Chicago")



load_state()


def getDate():
    current_date = datetime.now()

    current_day = current_date.day
    current_month = current_date.month
    current_year = current_date.year

    return current_day, current_month, current_year

day = 0
month = 0
year = 0

day, month, year = getDate()

def chartOranizer():
    global day, month, year, CDT, CMT, CYT
    current_day, current_month, current_year = getDate()
    if day != current_day:
        if CDT:
            CMT.append(sum(CDT))
            CDT.clear()
    if month != current_month:
        if CMT:
            CYT.append(sum(CMT))
            CMT.clear()
    if year != current_year:
        CYT.clear()
    
    day = current_day
    month = current_month
    year = current_year
    save_state()

def clearDayData():
    global agents, logs
    # ------------ agent data ------------
    for agent in agents:
        agents[agent]["todaysProfit"] = 0
        agents[agent]["currentStock"] = "null"
        agents[agent]["tradeHistory"] = []
    # ------------ logs ------------
    logs.clear()
    save_state()



# ---------------------- 12:02 checker ----------------------

def daily_1202_checker():
    global hour, minute, agents_to_delete, agents, timeZone

    last_run_date = None

    while True:
        # Use the selected timezone
        now = datetime.now(ZoneInfo(timeZone))

        # Run once per day at the specified hour/minute in that timezone
        if now.hour == hour and now.minute == minute:
            if last_run_date != now.date():
                chartOranizer()
                clearDayData()
                print("organized chart", flush=True)
                last_run_date = now.date()

        # Delete agents when stock market is closed
        if agents_to_delete and not is_us_stock_market_open():
            for agent in agents_to_delete.copy():
                if agent in agents:
                    del agents[agent]
                agents_to_delete.remove(agent)

            save_state()

        time.sleep(1)



worker = threading.Thread(target=daily_1202_checker, daemon=True)
worker.start()

print("worker thread started")


    


# ---------------------- 12:02 checker ----------------------

def is_us_stock_market_open(now: datetime | None = None) -> bool:
    # True = OPEN | False = CLOSED
    nyse = mcal.get_calendar("NYSE")

    if now is None:
        now = datetime.now(ZoneInfo("America/New_York"))
    elif now.tzinfo is None:
        raise ValueError("Pass a timezone-aware datetime, or leave now as None.")

    # Convert to UTC because pandas_market_calendars schedules are UTC-based.
    now_utc = pd.Timestamp(now).tz_convert("UTC")

    # Pull a small window around today so early closes/holidays are included.
    start_date = (now_utc - pd.Timedelta(days=7)).date()
    end_date = (now_utc + pd.Timedelta(days=7)).date()

    schedule = nyse.schedule(start_date=start_date, end_date=end_date)

    if schedule.empty:
        return False

    try:
        return bool(nyse.open_at_time(schedule, now_utc, only_rth=True))
    except ValueError:
        return False










@app.get("/")
def root():
    return {"status": "ok"}



@app.get("/local-time")
def get_local_time():
    return {"time": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M:%S %p %Z")}
    

@app.get("/set-reset-time")
def setResetTime(h: int, m: int, tz: str):
    global hour, minute, timeZone
    hour = h
    minute = m
    timeZone = tz
    save_state()
    return {"status": "updated"}

@app.get("/clear-mprofit")
def clearMprofit():
    global months_profit
    months_profit = 0
    return {"status": "cleared"}




OC_status = ""
agent_status = "active"



# ------------- home page -------------
@app.get("/get-home-page")
def getHomePage():
    global months_profit, OC_status, agents

    
    totalPositiveTrades = 0
    totalTrades = 0
    if agents:
        for a in agents:
            trades = []
            trades.extend(agents[a]["tradeHistory"])
            if trades:
                PositiveTrades = len(trades)
                totalTrades += len(trades)
                start = 0
                if trades[0] < 0:
                    PositiveTrades -= 1

                for i in range(1,len(trades)):
                    if trades[start] > trades[i]:
                        PositiveTrades -= 1

                    start += 1
                
                totalPositiveTrades += PositiveTrades
        if totalTrades:
            winRate = (totalPositiveTrades/totalTrades)*100
        else:
            winRate = 0.0
        if winRate:
            return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": totalTrades, "Active_Agents": len(agents), "Win_Rate": round(winRate)}
        else:
            return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": totalTrades, "Active_Agents": len(agents), "Win_Rate": "NA"}
    else:
        return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": totalTrades, "Active_Agents": 0, "Win_Rate": "NA"}




@app.get("/pause")
def pause_agents():
    global pause_status
    pause_status = True
    save_state()
    return {"status": "Pausing"}

@app.get("/E-stop")
def Emergency_stop():
    global E_stop_status
    E_stop_status = True
    save_state()
    return {"status": "E-stopping"}

@app.get("/resume")
def resumeAgents():
    global pause_status, E_stop_status
    pause_status = False
    E_stop_status = False
    save_state()
    return {"status": "Resuming"}



# ------------- logs page -------------

@app.get("/update-logs")
def update_logs(log: str):
    global logs
    logs.append(log)
    return {"status": "recieved"}
    
@app.get("/get-logs")
def get_logs():
    global logs
    return logs



# ------------- chart page -------------

@app.get("/get-chart-page")
def getChartPage(time: str):
    global CDT, CMT, CYT
    
    if time == "day":
        if CDT:
            data = {
                "totalProfit": CDT[-1],
                "plotPoints": CDT
            }
            return {"data": data}
        else:
            return {"data": "NA"}
    if time == "month":
        if CMT:
            data = {
                "totalProfit": CDT[-1],
                "plotPoints": CMT
            }
            return {"data": data}
        else:
            return {"data": "NA"}
    if time == "year":
        if CYT:
            data = {
                "totalProfit": CDT[-1],
                "plotPoints": CYT
            }
            return {"data": data}
        else:
            return {"data": "NA"}
    
    return {"Error": "invalid time"}


@app.get("/clear-chart-data")
def clearChartData():
    global CDT, CMT, CYT
    CDT.clear()
    CMT.clear()
    CYT.clear()
    return {"status": "cleared"}

# ------------- agents page -------------
# from app
@app.get("/add-agent")
def addAgent(ID: str, Aname: str):
    global agents
    if Aname not in agents:
        agents_to_add.update({Aname: ID})
        return {"Status": "Adding"}
    else:
        return {"status": "Agent already exists"}

# app pings this until the agent is launched
@app.get("/get-adding-status")
def getAddingStatus(Aname: str):
    for name in agents_to_add:
        if name == Aname:
            return {"Status": "Adding"}
    return {"Status": "Added"}


@app.get("/get-agent-page")
def getAgentPage():
    global agents
    return agents

"""
Should look like
    {
    "A1": {
        "todaysProfit": 128,
        "status": "waiting",
        "currentStock": null,
        "tradeHistory": [20, 44, 79, 65, 90, 124, 119, 147]
    },
    "A2": {
        "todaysProfit": 84,
        "status": "trading",
        "currentStock": "NVDA",
        "tradeHistory": [8, 22, 18, 41, 57, 73, 69, 96]
    },
    "A3": {
        "todaysProfit": -12,
        "status": "not active",
        "currentStock": null,
        "tradeHistory": [-10, 4, 18, 12, 31, 44, 39, 52]
    },

"""

# ------------- agent data update -------------
"""
this section is where the agents come 
to update the data associated to them
"""

@app.get("/update-agent-data")
def updateAgentData(Aname: str, TP: float, status: str, currentStock: str):
    global agents, months_profit, CDT
    if Aname in agents:
        if TP:
            months_profit += float(TP)
            CDT.append(months_profit)
            if agents[Aname]["tradeHistory"]:
                lastP = agents[Aname]["tradeHistory"][-1]
                newP = lastP + float(TP)
                agents[Aname]["tradeHistory"].append(newP)
            else:
                agents[Aname]["tradeHistory"].append(TP)
                
            agents[Aname]["todaysProfit"] = agents[Aname]["tradeHistory"][-1]
        if status:
            agents[Aname]["status"] = status
        if currentStock:
            agents[Aname]["currentStock"] = currentStock
        save_state()
        return {"status": "updated"}
    else:
        return {"Error": "name not in saved Agents"}



@app.get("/remove-agent")
def removeAgent(Aname: str):
    global agents

    if Aname in agents:
        if not is_us_stock_market_open():
            del agents[Aname]
            save_state()
            return {"status": "agent deleted"}
        else:
            agents_to_delete.append(Aname)
            return {"status": "agent scheduled for deletion"}
    else:
        return {"status": f"{Aname} does not exist"}
reallocated = []

@app.get("/request-reallocation")
def request_reallocation():
    global reallocated, agents
    if len(agents) >= 5:
        best = {"profit": 0, "agent": "", "sym": ""}
        for agent in agents:
            if agent not in reallocated:
                profit = agents[agent]["todaysProfit"]
                if profit > best["profit"]:
                    best["profit"] = profit
                    best["agent"] = agent
                    best["sym"] = agents[agent]["currentStock"]
        reallocated.append(best["agent"])
        if best["sym"]:
            return {"reallocation": best["sym"]}
        else:
            return {"reallocation": False}
    else:
        return {"reallocation": False}


# ------------- orchestrator ping -------------
# OC comes here every 10 sec or so
@app.get("/ping_from_OC")
def ping(status: str):
    global OC_status, agents_to_add, agent_status, pause_status, E_stop_status
    OC_status = status
    # Eg: downloading data
    return {"AgentsToAdd": agents_to_add, "AgentStatus": agent_status, "PauseStatus": pause_status, "E-StopStatus": E_stop_status}



# OC comes here when it has launched a new agent
@app.get("/added_agent")
def addedAgent(Aname: str, ID: str):
    global agents_to_add, agents
    if Aname in agents_to_add:
        agents.update({Aname: {
        "todaysProfit": 0,
        "status": "waiting",
        "currentStock": "null",
        "tradeHistory": [],
        "ID": ID
}})
        del agents_to_add[Aname]
        save_state()
        return {"Status": "Recieved"}
    else:
        return {"Error": "agent was not requested"}
    

# for Orchestrator
@app.get("/refresh-agents")
def getAgents():
    formated = {}
    global agents
    for agent in agents:
        formated.update({agent: agents[agent]['ID']})
    
    return formated


# ------------- orchestrator ping -------------




@app.post("/load-agents")
def load_agents(payload: Dict):
    global agents
    for agent in payload:
        agents.update({agent: {
        "todaysProfit": 0,
        "status": "waiting",
        "currentStock": "null",
        "tradeHistory": [],
        "ID": ""
}})
    save_state()
    return {"status": "updated", "agents": agents}

@app.get("/clear-agents")
def clear_agents():
    global agents, months_profit
    months_profit = 0.0
    agents.clear()
    save_state()
    return {"status": "cleared"}

endpoints = []
for route in app.routes:
    hi = ["/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"]
    if route.path not in hi:
        print("http://127.0.0.1:8000"+route.path)
        endpoints.append(route.path)

@app.get("/endpoints")
def getendpoints():
    global endpoints
    return {"endpoints": endpoints}

# Deploy code:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


"""
# Testing code:
if __name__ == "__main__":
    uvicorn.run("Sleepy_API_v1:app", host="127.0.0.1", port=8000, reload=True)
"""

# Querei: http://127.0.0.1:8000/update-profit?value=1036.39871243?Aname=hiiii
# Get: http://127.0.0.1:8000/total-profit