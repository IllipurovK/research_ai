import asyncio
import streamlit as st
from orchestrator import research_agent
from memory import Memory
from datetime import datetime

st.set_page_config(page_title="Research Agent", layout="wide")
st.title("🕵️ Research Agent")
st.markdown("Автоматический сбор информации из Wikipedia и DuckDuckGo")

# Боковая панель с настройками
with st.sidebar:
    st.header("Настройки")
    mode = st.selectbox("Режим", ["fast", "deep"], help="fast: 2-3 шага, короткие таймауты; deep: 5-7 шагов, долгие таймауты")
    st.markdown("---")
    st.caption("Powered by Qwen-Plus и DuckDuckGo")

# Основная область
topic = st.text_input("Тема исследования", placeholder="история интернета, квантовый компьютер, ...")

if st.button("🔍 Начать исследование", type="primary", disabled=not topic):
    with st.status("Исследование выполняется...", expanded=True) as status:
        st.write(f"Тема: **{topic}**")
        st.write(f"Режим: **{mode}**")
        
        import threading
        result_container = []   # сюда положим (memory, report)
        error_container = []    # сюда положим исключение
        
        def run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(research_agent(topic, mode))
                result_container.append(res)
            except Exception as e:
                error_container.append(e)
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=180)  # максимальное время deep режима + запас
        
        if error_container:
            st.error(f"Ошибка: {error_container[0]}")
            status.update(label="Ошибка выполнения", state="error")
        elif result_container:
            memory, report = result_container[0]
            status.update(label="Исследование завершено!", state="complete", expanded=False)
            st.success(f"✅ Исследование завершено. Выполнено шагов: {len(memory.steps)}, успешных: {len(memory.get_successful_steps())}")
            st.markdown("### 📄 Отчёт")
            st.markdown(report, unsafe_allow_html=False)
            
            st.download_button(
                label="📥 Скачать отчёт (Markdown)",
                data=report,
                file_name=f"{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
        else:
            st.error("Превышено время ожидания")
            status.update(label="Таймаут", state="error")


# streamlit run app.py