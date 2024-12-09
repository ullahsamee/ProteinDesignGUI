from common import *


state = st.session_state


def save(pdbs):
    out = active.parent / outdir
    out.mkdir(exist_ok=True)
    for i in pdbs:
        with open(out / i.name, 'wb') as f:
            f.write(i.getvalue())


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    outdir = 'diffusion'
    wildcard = f'{outdir}/*.pdb'

    st.title('Skip Designing')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    if active is not None:
        active = Path(active)
        with tab2:
            results = sorted(active.parent.glob(wildcard))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    with tab1:
        with st.form('form'):
            pdbs = st.file_uploader('Upload raw PDBs as design results', '.pdb', key='protein', accept_multiple_files=True)
            clicked = st.form_submit_button('UPLOAD', use_container_width=True, type='primary', disabled=active is None)

    if process_ongoing() and clicked:
        st.toast('Process busy!', icon="🚨")
    elif clicked:
        if pdbs:
            save(pdbs)
            st.success('All proteins uploaded.')
        else:
            st.error('Nothing to upload.')

    if process_ongoing():
        progress()
