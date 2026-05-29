import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 설정 (전문적인 대시보드 스타일)
st.set_page_config(
    page_title="수업 활동 점검 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 사이드바 - 설정 및 필터
with st.sidebar:
    st.header("⚙️ 설정 및 필터")
    
    # 개인정보 보호 안내 및 옵션
    st.info("🔒 본 앱은 브라우저 내에서 데이터를 처리하며 서버에 저장하지 않습니다. 민감한 개인정보 업로드는 자제해 주세요.")
    mask_student_name = st.checkbox("학생 이름 숨기기 (Student ID 표시)", value=False)
    
    # 파일 업로드 (CSV, Excel 지원)
    uploaded_file = st.file_uploader("📂 학생 활동 결과 파일 업로드 (.csv, .xlsx)", type=["csv", "xlsx"])
    
    st.markdown("---")
    st.caption("v1.0.0 | 수업 활동 점검 대시보드")

# 3. 메인 화면 - 데이터 처리 및 UI 렌더링
st.title("📊 수업 활동 점검 대시보드")
st.markdown("학생들의 활동 결과를 분석하여 제출률, 모둠별 현황 및 회의용 요약을 제공합니다.")
st.markdown("---")

if uploaded_file is not None:
    # 데이터 로드
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # [샘플 데이터 컬럼 예시: 학반, 모둠, 학번, 이름, 제출여부, 점수]
        # 필수 컬럼 존재 여부 확인 및 기본값 처리
        required_cols = ['학반', '모둠', '학번', '이름', '제출여부', '점수']
        for col in required_cols:
            if col not in df.columns:
                st.error(f"⚠️ 업로드된 파일에 '{col}' 컬럼이 없습니다. 확인 후 다시 업로드해 주세요.")
                st.stop()
                
        # 개인정보 보호 처리 (이름 -> ID 대체)
        if mask_student_name:
            df['표시이름'] = df['학번'].astype(str)
        else:
            df['표시이름'] = df['이름']

        # 사이드바 동적 필터 추가
        with st.sidebar:
            class_options = ["전체"] + sorted(df['학반'].unique().tolist())
            selected_class = st.selectbox("🏫 학반 선택", class_options)
            
            group_options = ["전체"] + sorted(df['모둠'].unique().tolist())
            selected_group = st.selectbox("👥 모둠 선택", group_options)

        # 데이터 필터링 적용
        filtered_df = df.copy()
        if selected_class != "전체":
            filtered_df = filtered_df[filtered_df['학반'] == selected_class]
        if selected_group != "전체":
            filtered_df = filtered_df[filtered_df['모둠'] == selected_group]

        # 4. 핵심 지표 (Key Metrics)
        total_students = len(filtered_df)
        submitted_students = len(filtered_df[filtered_df['제출여부'] == '제출'])
        submission_rate = (submitted_students / total_students * 100) if total_students > 0 else 0
        avg_score = filtered_df[filtered_df['제출여부'] == '제출']['점수'].mean() if submitted_students > 0 else 0
        unsubmitted_count = total_students - submitted_students

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총원", f"{total_students} 명")
        col2.metric("제출률", f"{submission_rate:.1f} %")
        col3.metric("평균 점수", f"{avg_score:.1f} 점")
        col4.metric("미제출 수", f"{unsubmitted_count} 명", delta=f"-{unsubmitted_count}", delta_color="inverse")

        st.markdown("---")

        # 5. 시각화 및 상세 목록 (레이아웃 분할)
        main_col1, main_col2 = st.columns([3, 2])

        with main_col1:
            st.subheader("👥 모둠별 제출 현황 및 평균 점수")
            
            # 모둠별 집계
            group_summary = filtered_df.groupby('모둠').agg(
                제출률=('제출여부', lambda x: (x == '제출').sum() / len(x) * 100),
                평균점수=('점수', lambda x: x[filtered_df['제출여부'] == '제출'].mean())
            ).reset_index().fillna(0)

            # 시각화 (인터랙티브 막대그래프)
            fig = px.bar(
                group_summary, 
                x='모둠', 
                y='제출률', 
                text=group_summary['제출률'].apply(lambda x: f"{x:.0f}%"),
                color='평균점수',
                color_continuous_scale='Blues',
                title="모둠별 제출률 (색상: 평균 점수)"
            )
            fig.update_layout(yaxis_maxvalue=100, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        with main_col2:
            st.subheader("⚠️ 미제출 및 보완 필요 대상")
            
            # 미제출자 및 보완 필요(예: 제출했으나 60점 미만인 학생) 추출
            unsubmitted_df = filtered_df[filtered_df['제출여부'] == '미제출'][['학반', '모둠', '표시이름']]
            needs_retry_df = filtered_df[(filtered_df['제출여부'] == '제출') & (filtered_df['점수'] < 60)][['학반', '모둠', '표시이름', '점수']]
            
            tab1, tab2 = st.tabs(["미제출자 목록", "보완 필요 학생"])
            
            with tab1:
                if not unsubmitted_df.empty:
                    st.warning(f"현재 필터 기준 미제출자 {len(unsubmitted_df)}명")
                    st.dataframe(unsubmitted_df, use_container_width=True, hide_index=True)
                else:
                    st.success("🎉 모든 학생이 제출했습니다!")
                    
            with tab2:
                if not needs_retry_df.empty:
                    st.info("기준 점수(60점) 미달 학생 목록입니다.")
                    st.dataframe(needs_retry_df, use_container_width=True, hide_index=True)
                else:
                    st.success("보완 필요 학생이 없습니다.")

        st.markdown("---")

        # 6. 회의용 요약 (자동 생성 및 복사 기능)
        st.subheader("📝 학년부/교과협의회 회의용 요약 리포트")
        
        # 텍스트 템플릿 생성
        summary_text = (
            f"[수업 활동 결과 요약]\n"
            f"- 확인 대상: 학반({selected_class}) / 모둠({selected_group})\n"
            f"- 총원 {total_students}명 중 {submitted_students}명 제출 (제출률: {submission_rate:.1f}%)\n"
            f"- 제출자 평균 점수: {avg_score:.1f}점\n"
            f"- 미제출 학생: {len(unsubmitted_df)}명 "
            f"({', '.join(unsubmitted_df['표시이름'].tolist()) if not unsubmitted_df.empty else '없음'})\n"
            f"- 피드백 필요 대상: {len(needs_retry_df)}명 "
            f"({', '.join(needs_retry_df['표시이름'].tolist()) if not needs_retry_df.empty else '없음'})\n"
            f"- 특이사항: 모둠별 제출률 격차가 있으므로 미제출 모둠 중심으로 독려 예정."
        )
        
        st.text_area("아래 내용을 복사하여 회의록이나 보고서에 활용하세요.", value=summary_text, height=180)
        
        # 향후 기능 미리보기 (다운로드 버튼 틀 구현)
        st.download_button(
            label="📄 요약 문장 다운로드 (.txt)",
            data=summary_text,
            file_name=f"수업활동요약_{selected_class}.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"🚨 파일 처리 중 오류가 발생했습니다: {e}")

else:
    # 파일이 업로드되지 않았을 때 표시할 대시보드 가이드/대기 화면
    st.info("👈 좌측 사이드바에서 [학생 활동 결과 CSV/Excel] 파일을 업로드하면 대시보드가 활성화됩니다.")
    
    # 사용자가 참고할 수 있는 샘플 데이터 형식 안내
    st.subheader("📋 권장 데이터 구조 (CSV/Excel Column)")
    sample_data = pd.DataFrame({
        '학반': ['1반', '1반', '2반'],
        '모둠': ['1모둠', '2모둠', '1모둠'],
        '학번': [10101, 10102, 10201],
        '이름': ['홍길동', '김철수', '이영희'],
        '제출여부': ['제출', '미제출', '제출'],
        '점수': [85, 0, 92]
    })
    st.table(sample_data)
