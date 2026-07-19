from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ortools.sat.python import cp_model
import uvicorn
import random

app = FastAPI(title="PGY Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScheduleRequest(BaseModel):
    staff: list
    requirements: dict
    daysInMonth: int


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/solve")
def solve_schedule(data: ScheduleRequest):
    model = cp_model.CpModel()
    num_staff = len(data.staff)
    days = data.daysInMonth
    
    shifts = {}
    for i in range(num_staff):
        for d in range(1, days + 1):
            shifts[(i, d, 0)] = model.NewBoolVar(f'staff_{i}_day_{d}_O')
            shifts[(i, d, 1)] = model.NewBoolVar(f'staff_{i}_day_{d}_N')

    staff_day_shifts = []
    staff_night_shifts = [] 
    shift_transitions = [] 

    for d in range(1, days + 1):
        req_d = data.requirements.get(str(d), {"dayShift": 2, "nightShift": 2})
        model.Add(sum(shifts[(i, d, 0)] for i in range(num_staff)) == req_d.get("dayShift", 2))
        model.Add(sum(shifts[(i, d, 1)] for i in range(num_staff)) == req_d.get("nightShift", 2))

    for i, staff in enumerate(data.staff):
        leave_days = staff.get("leaveRequests", [])
        
        for d in range(1, days + 1):
            model.AddAtMostOne([shifts[(i, d, 0)], shifts[(i, d, 1)]])
            
            if d in leave_days:
                model.Add(shifts[(i, d, 0)] == 0)
                model.Add(shifts[(i, d, 1)] == 0)
                
            if (d + 1) in leave_days:
                model.Add(shifts[(i, d, 1)] == 0)
                
            if d < days:
                model.Add(shifts[(i, d, 1)] + shifts[(i, d+1, 0)] <= 1)
            
            start_day_shift = model.NewBoolVar(f'start_day_{i}_{d}')
            if d == 1:
                model.Add(start_day_shift == shifts[(i, d, 0)])
            else:
                model.Add(start_day_shift >= shifts[(i, d, 0)] - shifts[(i, d-1, 0)])
            shift_transitions.append(start_day_shift)

            start_night_shift = model.NewBoolVar(f'start_night_{i}_{d}')
            if d == 1:
                model.Add(start_night_shift == shifts[(i, d, 1)])
            else:
                model.Add(start_night_shift >= shifts[(i, d, 1)] - shifts[(i, d-1, 1)])
            shift_transitions.append(start_night_shift)
                
        model.Add(shifts[(i, days, 1)] == 0)
        
        for d in range(1, days - 5):
            model.Add(sum(shifts[(i, d+k, 0)] + shifts[(i, d+k, 1)] for k in range(7)) <= 6)
            
        for d in range(1, days - 2):
            model.Add(sum(shifts[(i, d+k, 0)] for k in range(4)) <= 3)

        staff_day_shifts.append(sum(shifts[(i, d, 0)] for d in range(1, days + 1)))
        staff_night_shifts.append(sum(shifts[(i, d, 1)] for d in range(1, days + 1)))

    objective_terms = []

    # 預設永遠開啟：處理白班與夜班差距 (權重：100)
    max_day = model.NewIntVar(0, days, 'max_day')
    min_day = model.NewIntVar(0, days, 'min_day')
    model.AddMaxEquality(max_day, staff_day_shifts)
    model.AddMinEquality(min_day, staff_day_shifts)
    day_diff = model.NewIntVar(0, days, 'day_diff')
    model.Add(day_diff == max_day - min_day)
    
    max_night = model.NewIntVar(0, days, 'max_night')
    min_night = model.NewIntVar(0, days, 'min_night')
    model.AddMaxEquality(max_night, staff_night_shifts)
    model.AddMinEquality(min_night, staff_night_shifts)
    night_diff = model.NewIntVar(0, days, 'night_diff')
    model.Add(night_diff == max_night - min_night)

    objective_terms.append(day_diff * 100) 
    objective_terms.append(night_diff * 100) 

    # 預設永遠開啟：排班盡量連續 (權重：10)
    total_transitions = sum(shift_transitions)
    objective_terms.append(total_transitions * 10)

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    solver.parameters.random_seed = random.randint(1, 10000) 
    
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        result_schedule = {}
        for i, staff in enumerate(data.staff):
            staff_id = staff["id"]
            leave_days = staff.get("leaveRequests", [])
            result_schedule[staff_id] = {}
            for d in range(1, days + 1):
                result_schedule[staff_id][d] = {
                    "dayShift": solver.Value(shifts[(i, d, 0)]) == 1,
                    "nightShift": solver.Value(shifts[(i, d, 1)]) == 1,
                    "leave": d in leave_days
                }
        return {"status": "success", "schedule": result_schedule}
    else:
        return {"status": "failed", "message": "條件太嚴苛產生邏輯衝突，無法排出！請嘗試減少特定日期的需求人數或放寬排休條件。"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
