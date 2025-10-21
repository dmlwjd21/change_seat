import streamlit as st
import math
import pandas as pd
import re

st.set_page_config(page_title="교실 자리배치 랜덤 생성기", layout="wide")
st.title("교실 자리배치 랜덤 생성기 🪑")

# --- Helper functions ---

def parse_students(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # allow comma separated in a single line too
    students = []
    for ln in lines:
        parts = [p.strip() for p in re.split(r"[,;]", ln) if p.strip()]
        students.extend(parts)
    # remove duplicates while preserving order
    seen = set()
    out = []
    for s in students:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def parse_groups(text):
    # groups: each line contains members separated by commas
    groups = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = [p.strip() for p in ln.split(",") if p.strip()]
        if parts:
            groups.append(parts)
    return groups


def parse_specifics(text):
    # expect entries like: 이름(행,열) either comma separated or newline separated
    entries = []
    for ln in re.split(r"[,\n]", text):
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"^(.+?)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$", ln)
        if m:
            name = m.group(1).strip()
            r = int(m.group(2))
            c = int(m.group(3))
            entries.append((name, r, c))
        else:
            # ignore malformed but keep user-friendly by showing in session
            st.warning(f"특정 자리 지정 형식 오류: '{ln}'. 예: 홍길동(1,2)")
    return entries


def write_requirements():
    content = """
streamlit
pandas
"""
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


# --- UI: Inputs ---
with st.sidebar:
    st.header("입력")
    cols = st.number_input("열 개수 (한 행의 좌석 수)", min_value=1, max_value=20, value=5, step=1)

    st.markdown("---")
    st.subheader("학생 목록 (한 줄 또는 여러 줄, 쉼표 가능)")
    students_text = st.text_area("학생 이름을 입력하세요 (예: 홍길동)", height=200, placeholder="홍길동\n김철수, 이영희\n박민수")

    st.subheader("사이가 안 좋은 팀 (한 줄에 한 팀, 멤버는 쉼표로 구분)")
    groups_text = st.text_area("같은 행에 있으면 안 되는 학생 그룹을 입력하세요", height=120, placeholder="A,B,C\nD,E")

    st.subheader("특정 자리 배치 (형식: 이름(행,열), 예: 홍길동(1,2) )")
    specific_text = st.text_area("특정 학생을 특정 자리로 배치", height=120, placeholder="홍길동(1,1)\n이영희(2,3)")

    if st.button("자리 배치 생성/갱신"):
        st.session_state['generate'] = True

    st.markdown("---")
    if st.button("requirements.txt 파일 생성"):
        write_requirements()
        st.success("requirements.txt 파일을 현재 디렉터리에 생성했습니다.")

# parse inputs
students = parse_students(students_text)
groups = parse_groups(groups_text)
specifics = parse_specifics(specific_text)

n_students = len(students)
rows = math.ceil(n_students / cols) if n_students>0 else 0

# Initialize seating in session state
if 'seating' not in st.session_state:
    st.session_state['seating'] = {}
if 'rows' not in st.session_state:
    st.session_state['rows'] = rows
if 'cols' not in st.session_state:
    st.session_state['cols'] = cols

# If user clicked generate or if students changed, (re)generate layout
if st.session_state.get('generate') or (st.session_state.get('rows') != rows or st.session_state.get('cols') != cols):
    st.session_state['generate'] = False
    st.session_state['rows'] = rows
    st.session_state['cols'] = cols

    # basic placement algorithm with group-row separation
    seating = {(r+1, c+1): '' for r in range(max(rows,1)) for c in range(cols)}

    # Fill in specifics first (they may expand rows if needed)
    for name, r, c in specifics:
        # expand rows if necessary
        if r > rows:
            # expand rows
            extra = r - rows
            rows = r
            st.session_state['rows'] = rows
            for rr in range(rows - extra + 1, rows + 1):
                for cc in range(1, cols+1):
                    seating.setdefault((rr,cc),'')
        if (r,c) in seating:
            seating[(r,c)] = name
        else:
            st.warning(f"지정된 자리 {(r,c)}은(는) 현재 유효 범위를 벗어납니다.")

    # mark students already placed via specifics
    placed = set([v for v in seating.values() if v])

    # assign group members preferentially to different rows
    # create buckets per row
    row_buckets = {r+1: [] for r in range(rows)}

    # First, place members of each group round-robin across rows
    for grp in groups:
        row_idx = 1
        for member in grp:
            if member in placed:
                continue
            # find next row with free seats
            attempts = 0
            while attempts < rows:
                r = ((row_idx -1) % rows) + 1
                # count used seats in row
                used = sum(1 for c in range(1,cols+1) if seating.get((r,c)))
                if used < cols:
                    # assign to this row bucket (not exact column yet)
                    row_buckets[r].append(member)
                    placed.add(member)
                    row_idx += 1
                    break
                else:
                    row_idx +=1
                    attempts +=1
            # if all rows full, leave for later

    # remaining students (not in groups or could not place) go to a fill list
    remaining = [s for s in students if s not in placed]

    # now flatten buckets into final ordering row by row
    order = []
    for r in range(1, rows+1):
        # take bucket members first
        order.extend(row_buckets[r])
        # then fill with remaining up to row capacity
        cap = cols - len(row_buckets[r])
        take = remaining[:cap]
        order.extend(take)
        remaining = remaining[cap:]

    # if still remaining students, append new rows as needed
    extra_row = rows
    while remaining:
        extra_row += 1
        for c in range(1, cols+1):
            seating.setdefault((extra_row,c),'')
        take = remaining[:cols]
        idx = 0
        for name in take:
            seating[(extra_row, idx+1)] = name
            idx +=1
        remaining = remaining[cols:]

    # now place 'order' into seating row-major skipping specifics already placed
    idx = 0
    for r in range(1, max(rows,1)+1):
