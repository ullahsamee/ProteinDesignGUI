from common import *
import shutil

state = st.session_state


@st.dialog('Add a new trial')
def add():
    name = st.text_input('Trial Name')
    template = st.selectbox(
        "Select an existing trial as template",
        [None] + [str(i) for i in state['trials']],
    )
    if st.button('Confirm', use_container_width=True):
        assert name not in state['trials'], f"Trial {name} already exists."
        assert len(name) > 0, "Trial name cannot be empty."
        temp = Path(state['wkdir']) / name
        temp.mkdir(exist_ok=True)
        cfg = get_config(template)
        shutil.copytree(Path(template).parent / '*_input', temp)
        cfg['name'] = name
        p = temp / 'config.yml'
        put_config(cfg, p)
        state['trials'].append(p)
        st.rerun()


@st.dialog('Delete a trial')
def delete():
    st.write('Deleting an existing trial')
    to_del = st.selectbox(
        "Select an existing trial to delete",
        state['trials'],
    )
    if st.button('Confirm'):
        state['trials'].remove(to_del)
        shutil.rmtree(to_del.parent)
        st.rerun()


if __name__ == '__page__':
    st.title("Protein Design Applet")

    with st.form('path', border=False):
        c1, c2 = st.columns([3, 1], vertical_alignment='bottom')
        wkdir = c1.text_input('SET UP WORKING DIRECTORY', state['wkdir'],
                              placeholder='empty or with previous results')
        submit = c2.form_submit_button('Init', use_container_width=True)

    if submit:
        state['wkdir'] = wkdir
        assert validate_dir(wkdir), 'Invalid directory'
        wkdir = Path(wkdir)
        trials = state['trials'] = sorted(wkdir.rglob('*.yml'))

    if validate_dir(state['wkdir']):
        with st.expander('Trials', expanded=True):
            if len(state['trials']) > 0:
                df = []
                trials = state['trials']
                for t in trials:
                    c = get_config(t)
                    c = {'name': c['name'], **c['diffusion'], **c['fold'], **c['mpnn']}
                    c['contig'] = convert_selection(c['contig'])
                    c['inpaint'] = convert_selection(c['inpaint'])
                    c['fixed'] = convert_selection(c['fixed'])
                    df.append(pd.DataFrame([c]))
                df = pd.concat(df, ignore_index=True)
                df.set_index('name', inplace=True)
                st.dataframe(df, use_container_width=True)

            c1, c2 = st.columns(2)
            b1 = c1.button('Add', use_container_width=True, on_click=add)
            b2 = c2.button('Delete', use_container_width=True, on_click=delete,
                           disabled=len(state['trials']) == 0, type='primary')

    if process_ongoing():
        progress()