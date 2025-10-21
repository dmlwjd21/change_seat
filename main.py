import streamlit as st
import random
import numpy as np

st.set_page_config(page_title="랜덤 자리 배치기", layout="wide")

st.title("🎲 학생 랜덤 자리 배치기")

# --- 입력 받기 ---

num_students = st.number_input("총 학생 수", min_value=1, step=1)
num_cols = st.number_input("열(가로 칸) 수", min_value=1, step=1)

# 자동 행 계산
if num_students > 0 and num_cols > 0:
    num_rows = (num_students + num_cols - 1) // num_cols
    total_seats = num_rows * num_cols

    st.markdown(f"총 `{num_rows}행 x {num_cols}열 = {total_seats}`개의 자리가 필요합니다.")

# 빈 자리 입력
empty_seats_input = st.text_input("빈 자리를 입력하세요 (예: 1,5 / 2,3):", help="형식: 행,열 (여러 개는 줄바꿈 또는 쉼표로 구분)")
empty_seats = set()
if empty_seats_input:
    for item in empty_seats_input.replace('\n', ',').split(','):
        item = item.strip()
        if item and ',' in item:
            try:
                r, c = map(int, item.split(','))
                empty_seats.add((r, c))
            except:
                st.warning(f"잘못된 입력: {item}")

# 떨어뜨릴 학생들 (쌍 입력)
separated_pairs_input = st.text_area("떨어뜨릴 학생 쌍 입력 (예: 철수-영희)", help="한 줄에 한 쌍. 형식: 이름1-이름2")
separated_pairs = set()
if separated_pairs_input:
    for line in separated_pairs_input.splitlines():
        if "-" in line:
            a, b = map(str.strip, line.strip().split("-"))
            if a and b:
                separated_pairs.add((a, b))

# 고정할 학생들 (형식: 이름:행,열)
fixed_positions_input = st.text_area("고정할 학생들 입력 (예: 민수:2,3)", help="한 줄에 한 명. 형식: 이름:행,열")
fixed_positions = {}
if fixed_positions_input:
    for line in fixed_positions_input.splitlines():
        if ":" in line and "," in line:
            name, pos = line.strip().split(":")
            r, c = map(int, pos.strip().split(","))
            fixed_positions[name.strip()] = (r, c)

# 학생 이름 리스트
students_input = st.text_area("학생 이름 목록", help="한 줄에 한 명씩 입력")
students = [name.strip() for name in students_input.splitlines() if name.strip()]

if st.button("자리 배치 시작"):
    if len(students) != num_students:
        st.error("학생 수와 이름 수가 맞지 않습니다.")
    else:
        # 자리 목록 만들기
        seats = [(r, c) for r in range(1, num_rows+1) for c in range(1, num_cols+1)]
        available_seats = [s for s in seats if s not in empty_seats]

        if len(available_seats) < len(students):
            st.error("사용 가능한 자리가 부족합니다.")
        else:
            # 자리 고정 먼저 배치
            assigned = {}
            used_seats = set()

            for name, pos in fixed_positions.items():
                if pos in used_seats or pos in empty_seats or pos not in seats:
                    st.error(f"{name}의 자리 {pos}는 사용할 수 없습니다.")
                    st.stop()
                assigned[name] = pos
                used_seats.add(pos)

            # 나머지 학생들 랜덤 배치
            remaining_students = [s for s in students if s not in fixed_positions]
            remaining_seats = [s for s in available_seats if s not in used_seats]

            success = False
            max_attempts = 1000

            for _ in range(max_attempts):
                random.shuffle(remaining_students)
                trial_assignment = dict(zip(remaining_students, remaining_seats))

                # 고정된 것도 포함하여 전체 자리 배치 dict
                full_assignment = assigned.copy()
                full_assignment.update(trial_assignment)

                # 떨어져야 하는 학생들 검사
                def is_adjacent(pos1, pos2):
                    r1, c1 = pos1
                    r2, c2 = pos2
                    return abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1

                conflict = False
                for a, b in separated_pairs:
                    if a in full_assignment and b in full_assignment:
                        if is_adjacent(full_assignment[a], full_assignment[b]):
                            conflict = True
                            break

                if not conflict:
                    assigned = full_assignment
                    success = True
                    break

            if not success:
                st.error("제약 조건을 만족하는 자리를 찾지 못했습니다. 입력을 확인해 주세요.")
            else:
                # 자리표 그리기
                seat_grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
                for name, (r, c) in assigned.items():
                    seat_grid[r - 1][c - 1] = name

                st.success("자리 배치 완료 🎉")
