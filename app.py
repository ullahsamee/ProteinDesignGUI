from common import *


if __name__ == '__main__':
    st.set_page_config(page_title="Protein Design", page_icon="🧬")
    state = st.session_state

    if 'trials' not in state:
        state['trials'] = []
    if 'wkdir' not in state:
        state['wkdir'] = ''
    if 'process' not in state:
        state['process'] = None
    if 'auto' not in state:
        state['auto'] = None

    pg = st.navigation(
        {
            "": [st.Page('home.py', title="Getting Started")],
            "Design": [st.Page('scaffolding.py', title='Motif Scaffolding', icon="🎏")],
            "Export": [st.Page('mpnn.py', title='ProteinMPNN', icon="🎢"),
                       st.Page('colabfold.py', title='ColabFold', icon="🛝"),
                       st.Page('qc.py', title='Quality Control', icon="📐")],
        }
    )

    state = st.session_state

    st.sidebar.selectbox('Select a trial', state['trials'], key='current_trial')
    st.sidebar.subheader('Process Automation')

    st.sidebar.toggle('Automatic ProteinMPNN', False, key='proceed1')
    st.sidebar.toggle('Automatic ColabFold', False, key='proceed2')
    st.sidebar.divider()
    st.sidebar.button('Abort Process', on_click=abort_proc, type='primary', use_container_width=True)
    pg.run()