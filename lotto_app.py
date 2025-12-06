import streamlit as st
import google.generativeai as genai

# [수정된 부분]
# 이제 코드에 직접 키를 적지 않고, Streamlit의 비밀 금고(secrets)에서 가져옵니다.
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    # 로컬(내 컴퓨터)에서 테스트할 때를 위한 예외 처리 (선택 사항)
    # 배포할 때는 이 부분이 실행되지 않고 위에서 키를 가져옵니다.
    GOOGLE_API_KEY = "여기에_로컬_테스트용_키를_넣어도_됩니다_하지만_업로드는_조심"

genai.configure(api_key=GOOGLE_API_KEY)



# --- [핵심 기능] 사용 가능한 모델을 자동으로 찾아오는 함수 ---
def find_best_model():
    try:
        # 1. 구글 서버에 있는 모든 모델 목록을 가져옴
        available_models = []
        for m in genai.list_models():
            # 'generateContent' (텍스트 생성) 기능을 지원하는 모델만 골라냄
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if not available_models:
            return None, "사용 가능한 모델을 찾지 못했습니다. API 키를 확인해주세요."

        # 2. 우선순위 정하기 (Flash -> Pro -> 1.0 Pro -> 아무거나)
        best_model = None
        
        # (1순위) 빠르고 최신인 1.5 Flash
        for model_name in available_models:
            if "gemini-1.5-flash" in model_name:
                best_model = model_name
                break
        
        # (2순위) 똑똑한 1.5 Pro
        if not best_model:
            for model_name in available_models:
                if "gemini-1.5-pro" in model_name:
                    best_model = model_name
                    break
        
        # (3순위) 가장 대중적인 Pro
        if not best_model:
            for model_name in available_models:
                if "gemini-pro" in model_name:
                    best_model = model_name
                    break
        
        # (4순위) 정 없으면 목록의 첫 번째 것
        if not best_model:
            best_model = available_models[0]

        return best_model, None # 성공 시 모델 이름 반환

    except Exception as e:
        return None, str(e)

# --- 로또 번호 생성 함수 ---
def get_lotto_number(keyword):
    # 1. 모델 자동 탐색 시작
    model_name, error_msg = find_best_model()
    
    if error_msg:
        return f"오류 발생: {error_msg}", None

    # 2. 찾아낸 모델로 설정
    model = genai.GenerativeModel(model_name)
    
    # 3. 프롬프트 (기존과 동일)
    prompt = f"""
    당신은 사용자의 키워드에서 행운을 찾아내는 '운명적 로또 번호 생성기'입니다. 
    **[분석 대상 키워드]: {keyword}**

    아래의 엄격한 규칙에 따라 6개의 숫자를 추천하고, 그 이유를 스토리텔링 하세요.

    ### 1. 기본 원칙
    - **범위:** 1 ~ 45 사이의 자연수만 사용합니다.
    - **개수:** 정확히 6개의 숫자를 출력합니다.
    - **중복 불가:** 6개의 숫자 중 겹치는 숫자는 절대 없어야 합니다.

    ### 2. 번호 추출 로직
    1. **정보 검색:** Google 검색 지식을 활용해 '{keyword}'와 관련된 숫자 정보(생년월일, 나이, 데뷔일, 기념일, 주가 등)를 찾습니다.
    2. **숫자 변환:** 찾은 숫자가 1~45 범위를 벗어나면 덧셈/뺄셈을 통해 변환합니다.
    3. **부족한 숫자 채우기:** 나머지는 랜덤으로 채웁니다.

    ### 3. 답변 형식
    **🎱 [{keyword}]의 기운이 담긴 행운 번호**
    # 번호1 , 번호2 , 번호3 , 번호4 , 번호5 , 번호6

    **🔮 운명의 해석**
    * **[숫자1]:** (이유 설명)
    * **[숫자2]:** (이유 설명)
    * **[나머지]:** 부족한 운은 우주가 채워준 랜덤 행운 숫자입니다!
    
    ---
    *주의: 이 번호는 재미로만 즐겨주세요!*
    """
    
    # 답변 생성
    response = model.generate_content(prompt)
    return response.text, model_name # 결과와 사용된 모델 이름을 같이 반환

# --- 앱 화면 구성 (UI) ---
st.set_page_config(page_title="운명의 로또", page_icon="🎱")

st.title("🎰 운명의 로또 생성기")
st.subheader("키워드를 입력하면 우주가 번호를 점지해줍니다.")
st.caption("AI가 자동으로 최적의 모델을 탐색하여 실행합니다.")
st.markdown("---")

keyword = st.text_input("행운을 찾고 싶은 키워드는? (예: 손흥민, 내 생일, 삼성전자)", "")

if st.button("🔮 번호 추출하기", type="primary"):
    if keyword:
        with st.spinner(f"'{keyword}'의 기운을 분석할 모델을 찾는 중..."):
            try:
                result, used_model = get_lotto_number(keyword)
                
                if used_model: # 성공했을 때
                    st.success(f"추출 성공! (사용된 두뇌: {used_model})")
                    st.markdown(result)
                else: # 모델 찾기 실패 등 에러
                    st.error(result)
                    
            except Exception as e:
                st.error("알 수 없는 오류가 발생했습니다.")
                st.error(f"내용: {e}")
    else:
        st.warning("키워드를 먼저 입력해주세요!")