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


# ---------------------- 12:02 checker ----------------------
logs = []
def daily_1202_checker():
    global logs
    last_run_date = None

    while True:
        now = datetime.now()

        # Check for exactly 12:02 AM
        if now.hour == 0 and now.minute == 2:
            # Make sure it only runs once per day
            if last_run_date != now.date():
                chartOranizer()
                logs.clear()
                print("organized chart", flush=True)
                last_run_date = now.date()

        # Check every second
        time.sleep(1)



worker = threading.Thread(target=daily_1202_checker, daemon=True)
worker.start()

print("worker thread started")


    


# ---------------------- 12:02 checker ----------------------




@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/-------------END-POINTS---------------") # Litterly just a seprator for printing endpoints
def stfu():
    return "stfu"



agents = {}
months_profit = 0  #this is where the total month's profit is stored

agents_to_add = {}
"""
looks like:

{"a1": ID, "a2": ID}
"""


OC_status = ""
agent_status = "active"



# ------------- home page -------------
@app.get("/get-home-page")
def getHomePage():
    global months_profit, OC_status, agents

    trades = []
    if agents:
        for a in agents:
            trades.extend(agents[a]["tradeHistory"])
        if trades:
            PositiveTrades = len(trades)
            for t in trades:
                if t < 0:
                    PositiveTrades -= 1
            winRate = (PositiveTrades/len(trades))*100

            return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": len(trades), "Active_Agents": len(agents), "Win_Rate": round(winRate)}
        else:
            return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": 0, "Active_Agents": len(agents), "Win_Rate": "NA"}
    else:
        return {"Total_Profit": months_profit, "Status": OC_status, "Trades_Today": 0, "Active_Agents": 0, "Win_Rate": "NA"}



pause_status = False
E_stop_status = False
@app.get("/pause")
def pause_agents():
    global pause_status
    pause_status = True
    return {"status": "Pausing"}

@app.get("/E-stop")
def Emergency_stop():
    global E_stop_status
    E_stop_status = True
    return {"status": "E-stopping"}

@app.get("/resume")
def resumeAgents():
    global pause_status, E_stop_status
    pause_status = False
    E_stop_status = False
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
                "totalProfit": sum(CDT),
                "plotPoints": CDT
            }
            return {"data": data}
        else:
            return {"data": "not enough data yet"}
    if time == "month":
        if CMT:
            data = {
                "totalProfit": sum(CMT),
                "plotPoints": CMT
            }
            return {"data": data}
        else:
            return {"data": "not enough data yet"}
    if time == "year":
        if CYT:
            data = {
                "totalProfit": sum(CYT),
                "plotPoints": CYT
            }
            return {"data": data}
        else:
            return {"data": "not enough data yet"}
    
    return {"Error": "invalid time"}




# ------------- agents page -------------
# from app
@app.get("/add-agent")
def addAgent(ID: str, Aname: str):
    agents_to_add.update({Aname: ID})
    return {"Status": "Adding"}

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
        return {"status": "updated"}
    else:
        return {"Error": "name not in saved Agents"}








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
def addedAgent(Aname: str):
    global agents_to_add, agents_format, agents
    if Aname in agents_to_add:
        agents.update({Aname: {
        "todaysProfit": 0,
        "status": "waiting",
        "currentStock": "null",
        "tradeHistory": []
}})
        del agents_to_add[Aname]
        return {"Status": "Recieved"}
    else:
        return {"Error": "agent was not requested"}
    

"""
the oc will come here to save the agents data at the end
of the day to ensure that the data is save incase the API gets rebooted
"""
@app.get("/get-agents")
def getAgents():
    global agents
    return agents


# ------------- orchestrator ping -------------




@app.post("/load-agents")
def load_agents(payload: Dict):
    global agents
    for agent in payload:
        agents.update({agent: {
        "todaysProfit": 0,
        "status": "waiting",
        "currentStock": "null",
        "tradeHistory": []
}})
    return {"status": "updated", "agents": agents}

@app.get("/clear-agents")
def clear_agents():
    global agents
    agents.clear()
    return {"status": "cleared"}


for route in app.routes:
    hi = ["/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"]
    if route.path not in hi:
        print("http://127.0.0.1:8000"+route.path)

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