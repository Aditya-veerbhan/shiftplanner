
import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

def generate_shift_roster(shift_data, start_date, end_date, pa_names, wfh_limit):
    dates = pd.date_range(start=start_date, end=end_date)
    shifts = {shift['name']: {"type": shift['type'], "hc": shift['hc'], "timing": shift['timing']} for shift in shift_data}

    schedule = {date.strftime('%Y-%m-%d'): {shift: [] for shift in shifts} for date in dates}
    wfh_count = {pa: 0 for pa in pa_names}
    weekly_shift_count = {pa: 0 for pa in pa_names}

    for date in dates:
        used_today = set()
        for shift_name, shift_info in shifts.items():
            required_hc = shift_info["hc"]
            shift_type = shift_info["type"]

            available_pa = [pa for pa in pa_names if pa not in used_today and weekly_shift_count[pa] < len(dates)]
            if shift_type == "WFH":
                eligible_pa = [pa for pa in available_pa if wfh_count[pa] < wfh_limit]
            else:
                eligible_pa = available_pa

            if len(eligible_pa) < required_hc:
                eligible_pa = [pa for pa in pa_names if pa not in used_today and weekly_shift_count[pa] < len(dates)]
            if len(eligible_pa) < required_hc:
                eligible_pa = [pa for pa in pa_names if pa not in used_today]

            chosen = random.sample(eligible_pa, min(required_hc, len(eligible_pa)))
            schedule[date.strftime('%Y-%m-%d')][shift_name] = chosen

            for pa in chosen:
                used_today.add(pa)
                weekly_shift_count[pa] += 1
                if shift_type == "WFH":
                    wfh_count[pa] += 1

    rows = []
    for date, shifts_data in schedule.items():
        for shift, pas in shifts_data.items():
            for pa in pas:
                rows.append({
                    "Date": date,
                    "Shift Name": shift,
                    "Shift Timing": shifts[shift]['timing'],
                    "Shift Type": shifts[shift]['type'],
                    "PA Name": pa
                })

    df_schedule = pd.DataFrame(rows)
    df_schedule = df_schedule.sort_values(by=["Date", "Shift Name"])

    shift_summary = df_schedule.groupby(['PA Name', 'Shift Name']).size().unstack(fill_value=0)
    shift_summary['Total Shifts'] = shift_summary.sum(axis=1)
    wfh_shifts = [s['name'] for s in shift_data if s['type'] == "WFH"]
    shift_summary['WFH Shifts'] = shift_summary[wfh_shifts].sum(axis=1)

    shift_details = pd.DataFrame(shift_data)

    return df_schedule, shift_summary, shift_details

st.title("📅 Shift Roaster Generator")

with st.form("shift_form"):
    shift_input = st.text_area("Enter Shift Details (one per line) in format: ShiftName | Timing | HC | Type (WFH/WFO)", 
        value="Early Morning | 07:00-16:00 | 1 | WFH\nMorning | 09:00-18:00 | 3 | WFO\nGeneral | 10:00-19:00 | 4 | WFO\nKit Kat | 10:00-14:00 & 19:00-23:00 | 3 | WFH")
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    pa_names = st.text_area("Enter PA Names (comma-separated)").split(",")
    wfh_limit = st.number_input("Max WFH Shifts per PA per week", min_value=1, value=2)

    submitted = st.form_submit_button("Generate Roaster")

if submitted:
    shift_data = []
    for line in shift_input.strip().split("\n"):
        try:
            name, time, hc, typ = [x.strip() for x in line.split("|")]
            shift_data.append({
                "name": f"{name} ({time})",
                "timing": time,
                "type": typ,
                "hc": int(hc)
            })
        except Exception as e:
            st.error(f"Error parsing line: {line} — make sure it's in correct format.")

    pa_names = [name.strip() for name in pa_names if name.strip()]

    if shift_data and pa_names:
        df_schedule, shift_summary, shift_details = generate_shift_roster(shift_data, start_date, end_date, pa_names, wfh_limit)

        with pd.ExcelWriter("shift_roaster_output.xlsx") as writer:
            df_schedule.to_excel(writer, sheet_name='Shift Schedule', index=False)
            shift_summary.to_excel(writer, sheet_name='Summary Stats')
            shift_details.to_excel(writer, sheet_name='Shift Info', index=False)

        with open("shift_roaster_output.xlsx", "rb") as file:
            st.download_button(label="📥 Download Shift Roaster Excel", data=file, file_name="Shift_Roaster.xlsx")
