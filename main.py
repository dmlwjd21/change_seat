import streamlit as st
import random
import numpy as np

st.set_page_config(page_title="랜덤 자리 배치기", layout="wide")

st.title("🎲 학생 랜덤 자리 배치기")

# --- 입력 받기 ---
num_students = st.number_input("총 학생 수", min_value=1, step=1, value=10)
num_cols    = st.number_input("열(가로 칸) 수", min_value=1, step=1, value=5)

if num_students > 0 and num_cols > 0:
    num_rows   = (num_students + num_cols - 1) // num_cols
    total_seats = num_rows * num_cols
    st.markdown(f"총 `{num_rows}행 × {num_cols}열 = {total_seats}`개의 자리가 필요합니다.")

# 학생 이름 목록
students_input = st.text_area("학생 이름 목록 (한 줄에 한 명씩)", help="한 줄에 한 학생 이름 입력")
students       = [name.strip() for name in students_input.splitlines() if name.strip()]

# 떨어뜨릴 학생들 (쌍 입력)
separated_pairs_input = st.text_area(
    "떨어뜨릴 학생 쌍 입력 (예: 철수-영희)", 
    help="한 줄에 한 쌍. 형식: 이름1-이름2"
)
separated_pairs = set()
if separated_pairs_input:
    for line in separated_pairs_input.splitlines():
        if "-" in line:
            a, b = map(str.strip, line.strip().split("-"))
            if a and b:
                separated_pairs.add((a, b))

# 고정할 학생들 (형식: 이름:행,열)
fixed_positions_input = st.text_area(
    "고정할 학생들 입력 (예: 민수:2,3)", 
    help="한 줄에 한 명. 형식: 이름:행,열"
)
fixed_positions = {}
if fixed_positions_input:
    for line in fixed_positions_input.splitlines():
        if ":" in line and "," in line:
            name, pos = line.strip().split(":")
            r, c = map(int, pos.strip().split(","))
            fixed_positions[name.strip()] = (r, c)

# 빈 자리 입력 — 초기 방식
empty_seats_input = st.text_input(
    "빈 자리를 입력하세요 (예: 1,5 / 2,3)", 
    help="형식: 행,열 (여러 개는 쉼표 또는 줄바꿈으로 분리)"
)
initial_empty_seats = set()
if empty_seats_input:
    for item in empty_seats_input.replace('\n', ',').split(','):
        item = item.strip()
        if item and ',' in item:
            try:
                r,c = map(int, item.split(','))
                initial_empty_seats.add((r, c))
            except:
                st.warning(f"잘못된 입력: {item}")

# 자리 배치 시작 버튼
if st.button("자리 배치 시작"):
    # 입력 검증
    if len(students) != num_students:
        st.error("학생 수와 이름 수가 맞지 않습니다.")
    else:
        seats = [(r, c) for r in range(1, num_rows+1) for c in range(1, num_cols+1)]
        available_seats = [s for s in seats if s not in initial_empty_seats]

        if len(available_seats) < len(students):
            st.error("사용 가능한 자리가 부족합니다.")
        else:
            # 고정 자리 배치
            assigned     = {}
            used_seats   = set()

            for name, pos in fixed_positions.items():
                if pos in used_seats or pos in initial_empty_seats or pos not in seats:
                    st.error(f"{name}의 자리 {pos}는 사용할 수 없습니다.")
                    st.stop()
                assigned[name] = pos
                used_seats.add(pos)

            remaining_students = [s for s in students if s not in fixed_positions]
            remaining_seats    = [s for s in available_seats if s not in used_seats]

            success      = False
            max_attempts = 1000

            def is_adjacent(pos1, pos2):
                r1, c1 = pos1
                r2, c2 = pos2
                return abs(r1-r2) <= 1 and abs(c1-c2) <= 1

            for _ in range(max_attempts):
                random.shuffle(remaining_students)
                trial_assignment = dict(zip(remaining_students, remaining_seats))
                full_assignment  = assigned.copy()
                full_assignment.update(trial_assignment)

                conflict = False
                for a, b in separated_pairs:
                    if a in full_assignment and b in full_assignment:
                        if is_adjacent(full_assignment[a], full_assignment[b]):
                            conflict = True
                            break

                if not conflict:
                    assigned = full_assignment
                    success  = True
                    break

            if not success:
                st.error("제약 조건을 만족하는 배치가 만들어지지 않았습니다. 입력을 확인하세요.")
            else:
                st.success("자리 배치 완료 🎉")
                # 자리표 화면 표시 + 클릭 가능한 빈 자리 지정
                seat_grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
                for name, (r,c) in assigned.items():
                    seat_grid[r-1][c-1] = name

                # 빈 자리 초기값 복사
                empty_seats = set(initial_empty_seats)

                st.markdown("### 자리표 (아래에서 빈 자리 클릭해 조정 가능)")
                for r in range(1, num_rows+1):
                    cols = st.columns(num_cols)
                    for c in range(1, num_cols+1):
                        idx = (r, c)
                        if idx in empty_seats:
                            # 빈 자리라면 버튼으로 표시
                            if cols[c-1].button(f"🪑 빈 자리 ({r},{c})", key=f"empty_{r}_{c}"):
                                # 클릭 시 빈자리 토글
                                if idx in empty_seats:
                                    empty_seats.remove(idx)
                                else:
                                    empty_seats.add(idx)
                                st.experimental_rerun()
                        elif seat_grid[r-1][c-1]:
                            name = seat_grid[r-1][c-1]
                            cols[c-1].markdown(f"**{name}**")
                        else:
                            # 할당되지 않은 자리
                            if cols[c-1].button(f"⬜ 자리 ({r},{c})", key=f"free_{r}_{c}"):
                                empty_seats.add(idx)
                                st.experimental_rerun()
