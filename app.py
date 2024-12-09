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
    if 'proceed1' in state:
        state['proceed1'] = state['proceed1']
    if 'proceed2' in state:
        state['proceed2'] = state['proceed2']
    if 'proceed3' in state:
        state['proceed3'] = state['proceed3']
    if 'process_args' not in state:
        state['process_args'] = None

    pg = st.navigation(
        {
            "": [st.Page('page_files/home.py', title="Getting Started")],
            "Design": [st.Page('page_files/scaffold.py', title='Motif Scaffolding', icon='🎏'),
                       st.Page('page_files/skip.py', title='Skip Designing', icon='📦')],
            "Export": [st.Page('page_files/mpnn.py', title='ProteinMPNN', icon='🎢'),
                       st.Page('page_files/colabfold.py', title='AlphaFold2 (ColabFold)', icon='🛝'),
                       st.Page('page_files/boltz.py', title='AlphaFold3 (Boltz-1)', icon='🛝')],
            "Analysis":[st.Page('page_files/qc.py', title='Quality Control', icon='📐')],
        }
    )

    state = st.session_state

    st.sidebar.selectbox('Select a trial', state['trials'], key='current_trial')
    st.sidebar.subheader('Process Automation')

    st.sidebar.toggle('Automatic ProteinMPNN', False, key='proceed1')
    st.sidebar.toggle('Automatic AlphaFold', False, key='proceed2')
    st.sidebar.toggle('Automatic Quality Control', False, key='proceed3')
    st.sidebar.divider()
    st.sidebar.button('Abort Process', on_click=abort_proc, type='primary', use_container_width=True)
    pg.run()