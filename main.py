# streamlit_seating.py
import streamlit as st
import math
import pandas as pd
import re
from typing import List, Tuple

st.set_page_config(page_title="교실 자리배치 랜덤 생성기", layout="wide")
st.title("교실 자리배치 랜덤 생성기 🪑")

# ---------------- Helper functions ----------------
def parse_students(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    students = []
    for ln in lines:
        parts = [p.strip() for p in re.split(r"[,;]", ln) if p.strip()]
        students.extend(parts)
    seen = set()
    out = []
    for s in students:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out

def parse_groups(text: str) -> List[List[str]]:
    groups = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = [p.strip() for p in ln.split(",") if p.strip()]
        if parts:
            groups.append(parts)
    return groups

def parse_specifics(text: str) -> List[Tuple[str,int,int]]:
    entries = []
    for ln in re.split(r"[,\\n]", text):
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
            # show warning in UI but continue
            st.warning(f"특정 자리 지정 형식 오류: '{ln}'. 예: 홍길동(1,2)")
    return entries

def write_requirements():
    content = """
streamlit
pandas
"""
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# ---------------- Sidebar / Inputs ----------------
with st.sidebar:
    st.header("입력")
    cols = st.number_input("열 개수 (한 행의 좌석 수)", min_value=1, max_value=20, value=5, step=1)

    st.markdown("---")
    st.subheader("학생 목록 (한 줄 또는 여러 줄, 쉼표 가능)")
    students_text = st.text_area("학생 이름을 입력하세요 (예: 홍길동)", height=200,
                                 placeholder="홍길동\n김철수, 이영희\n박민수")

    st.subheader("사이가 안 좋은 팀 (한 줄에 한 팀, 멤버는 쉼표로 구분)")
    groups_text = st.text_area("같은 행에 있으면 안 되는 학생 그룹을 입력하세요", height=120,
                               placeholder="A,B,C\nD,E")

    st.subheader("특정 자리 배치 (형식: 이름(행,열), 예: 홍길동(1,2) )")
    specific_text = st.text_area("특정 학생을 특정 자리로 배치", height=120,
                                 placeholder="홍길동(1,1)\n이영희(2,3)")

    if st.button("자리 배치 생성/갱신"):
        st.session_state['generate'] = True

    st.markdown("---")
    if st.button("requirements.txt 파일 생성"):
        write_requirements()
        st.success("requirements.txt 파일을 현재 디렉터리에 생성했습니다.")

# ---------------- Parse inputs & prepare ----------------
students = parse_students(students_text or "")
groups = parse_groups(groups_text or "")
specifics = parse_specifics(specific_text or "")

n_students = len(students)
rows = math.ceil(n_students / cols) if n_students > 0 else 0
rows = max(rows, 1)  # 최소 1행은 보여주기

# Initialize session state
if 'seating' not in st.session_state:
    st.session_state['seating'] = {}
if 'rows' not in st.session_state:
    st.session_state['rows'] = rows
if 'cols' not in st.session_state:
    st.session_state['cols'] = cols
if 'generate' not in st.session_state:
    st.session_state['generate'] = False

# If user clicked generate or dims changed, (re)generate layout
if st.session_state.get('generate') or (st.session_state.get('rows') != rows or st.session_state.get('cols') != cols):
    st.session_state['generate'] = False
    st.session_state['rows'] = rows
    st.session_state['cols'] = cols

    # Initialize seating dictionary for current rows & cols
    seating = {(r + 1, c + 1): '' for r in range(rows) for c in range(cols)}

    # Place specifics first, expand rows if needed
    max_row_needed = rows
    for name, r, c in specifics:
        if r < 1 or c < 1:
            st.warning(f"지정된 자리 {(r,c)}의 값이 1 이하입니다. 무시합니다: {name}({r},{c})")
            continue
        if c > cols:
            st.warning(f"지정된 자리 열 {c}은(는) 현재 열 수({cols})를 초과합니다. 무시합니다: {name}({r},{c})")
            continue
        if r > max_row_needed:
            # expand seating rows up to r
            for rr in range(max_row_needed + 1, r + 1):
                for cc in range(1, cols + 1):
                    seating.setdefault((rr, cc), '')
            max_row_needed = r
        seating[(r, c)] = name

    # Update rows if expanded
    rows = max_row_needed
    st.session_state['rows'] = rows

    # mark already placed
    placed = set([v for v in seating.values() if v])

    # prepare empty buckets per row
    row_buckets = {r + 1: [] for r in range(rows)}

    # Place group members preferentially into different rows (round-robin)
    for grp in groups:
        row_idx = 1
        for member in grp:
            if member in placed:
                continue
            attempts = 0
            while attempts < rows:
                r = ((row_idx - 1) % rows) + 1
                used = sum(1 for c in range(1, cols + 1) if seating.get((r, c)))
                if used < cols:
                    row_buckets[r].append(member)
                    placed.add(member)
                    row_idx += 1
                    break
                else:
                    row_idx += 1
                    attempts += 1
            # if couldn't place in any row, will treat as remaining

    # remaining students
    remaining = [s for s in students if s not in placed]

    # build ordered list by rows
    order = []
    for r in range(1, rows + 1):
        order.extend(row_buckets.get(r, []))
        cap = cols - len(row_buckets.get(r, []))
        if cap > 0:
            take = remaining[:cap]
            order.extend(take)
            remaining = remaining[cap:]

    # if still remaining, append extra rows until filled
    extra_row = rows
    while remaining:
        extra_row += 1
        for c in range(1, cols + 1):
            seating.setdefault((extra_row, c), '')
        take = remaining[:cols]
        for idx, name in enumerate(take):
            seating[(extra_row, idx + 1)] = name
        remaining = remaining[cols:]

    # finally, place 'order' into unfilled seats row-major
    idx = 0
    max_row_now = max(pos[0] for pos in seating.keys())
    for r in range(1, max_row_now + 1):
        for c in range(1, cols + 1):
            if seating.get((r, c)):
                continue
            if idx < len(order):
                seating[(r, c)] = order[idx]
                idx += 1
            else:
                seating[(r, c)] = ''

    st.session_state['seating'] = seating

# ---------------- Display grid ----------------
st.subheader(f"자리배치 (행: {st.session_state.get('rows',0)}  열: {st.session_state.get('cols',0)})")
seating = st.session_state.get('seating', {})
rows_display = st.session_state.get('rows', 0)
cols_display = st.session_state.get('cols', 0)

if rows_display == 0 or cols_display == 0:
    st.info("학생 목록을 입력하고 열 개수를 지정한 뒤 '자리 배치 생성/갱신' 버튼을 누르세요.")
else:
    # render each row as columns
    for r in range(1, rows_display + 1):
        cols_cells = st.columns(cols_display)
        for c in range(1, cols_display + 1):
            label = seating.get((r, c), '') or "(빈 자리)"
            # clicking sets seat to empty
            if cols_cells[c - 1].button(label, key=f"seat_{r}_{c}"):
                st.session_state['seating'][(r, c)] = ''
                # safe rerun to refresh UI
                st.experimental_rerun()

# 교탁 (교탁을 아래쪽에 표시)
st.markdown("---")
st.markdown("<div style='text-align:center; padding:16px; font-weight:bold;'>교탁 (앞쪽) — ▼ 위치: 아래</div>", unsafe_allow_html=True)

# Download seating as CSV
if seating:
    df_rows = []
    max_row = max([pos[0] for pos in seating.keys()])
    max_col = max([pos[1] for pos in seating.keys()])
    for r in range(1, max_row + 1):
        row_vals = [seating.get((r, c), '') for c in range(1, max_col + 1)]
        df_rows.append(row_vals)
    df = pd.DataFrame(df_rows)
    st.download_button("자리표 CSV로 다운로드", df.to_csv(index=False, header=False).encode('utf-8'), file_name='seating.csv')

# Show internal table for copy/paste
if seating:
    st.subheader("내부 데이터 (테이블)")
    st.write(df)

# sidebar help
st.sidebar.markdown("---")
st.sidebar.subheader("사용법 요약")
st.sidebar.markdown(
    "1. 왼쪽에 열 개수를 입력하고 학생 목록을 넣으세요.\n"
    "2. 사이가 안 좋은 학생 그룹은 한 줄에 1그룹씩, 멤버는 쉼표로 구분합니다.\n"
    "3. 특정 자리에 배치하려면 '이름(행,열)' 형식으로 입력하세요.\n"
    "4. '자리 배치 생성/갱신' 버튼을 누르면 자동으로 배치됩니다.\n"
    "5. 자리 버튼을 클릭하면 그 자리를 빈 자리로 바꿉니다.\n"
)

# ensure requirements file exists (create silently on first run)
try:
    open('requirements.txt', 'r')
except FileNotFoundError:
    write_requirements()
