import shutil
import json
from utils import *


@st.dialog('Add a new trial')
def add():
    name = st.text_input('Trial Name')
    template = st.selectbox(
        "Select an existing trial as template",
        [None] + [str(i) for i in st.session_state['trials']],
    )
    pdb = st.file_uploader('Input a PDB for motif reference (optional if with template)', '.pdb')
    if st.button('Confirm', use_container_width=True):
        assert name not in st.session_state['trials'], f"Trial {name} already exists."
        assert len(name) > 0, "Trial name cannot be empty."
        temp = Path(st.session_state['wkdir']) / name
        temp.mkdir(exist_ok=True)
        if template is not None:
            cfg = get_config(template)
            p = Path(template).parent
            shutil.copy(p / cfg['diffusion']['protein'], temp)
            shutil.copy(p / cfg['diffusion']['contig'], temp)
            shutil.copy(p / cfg['diffusion']['inpaint'], temp)
            shutil.copy(p / cfg['mpnn']['fixed'], temp)
        else:
            assert pdb is not None, 'You must have a protein for one trial.'
            with open('default.json', 'r') as f:
                cfg = json.load(f)
            nt = get_table(cfg, None)
            nt.to_csv(temp / cfg['diffusion']['inpaint'], index=False)
            nt.to_csv(temp / cfg['diffusion']['contig'], index=False)
            nt.to_csv(temp / cfg['mpnn']['fixed'], index=False)
        if pdb is not None:
            cfg['diffusion']['protein'] = pdb.name
            with open(temp / pdb.name, 'wb') as f:
                f.write(pdb.getvalue())
        cfg['name'] = name
        p = temp / 'config.yml'
        put_config(cfg, p)
        st.session_state['trials'].append(p)
        st.rerun()


@st.dialog('Delete a trial')
def delete():
    st.write('Deleting an existing trial')
    to_del = st.selectbox(
        "Select an existing trial to delete",
        st.session_state['trials'],
    )
    if st.button('Confirm'):
        st.session_state['trials'].remove(to_del)
        shutil.rmtree(to_del.parent)
        st.rerun()


if __name__ == '__main__':

    init()

    st.set_page_config(
        page_title="Protein Design",
    )

    st.title("Protein Design Applet")

    with st.form('path', border=False):
        c1, c2 = st.columns([3, 1], vertical_alignment='bottom')
        wkdir = c1.text_input('SET UP WORKING DIRECTORY', st.session_state['wkdir'],
                              placeholder='empty or with previous results')
        submit = c2.form_submit_button('Init', use_container_width=True)

    if submit:
        st.session_state['wkdir'] = wkdir
        assert validate_dir(wkdir), 'Invalid directory'
        wkdir = Path(wkdir)
        trials = st.session_state['trials'] = sorted(wkdir.rglob('*.yml'))

    if validate_dir(st.session_state['wkdir']):
        with st.expander('Trials', expanded=True):
            if len(st.session_state['trials']) > 0:
                df = []
                trials = st.session_state['trials']
                for t in trials:
                    c = get_config(t)
                    c = {'name': c['name'], **c['diffusion'], **c['fold'], **c['mpnn']}
                    c['contig'] = convert_selection(get_table(t, 'contig'))
                    c['inpaint'] = convert_selection(get_table(t, 'inpaint'))
                    c['fixed'] = convert_selection(get_table(t, 'fixed'))
                    df.append(pd.DataFrame([c]))
                df = pd.concat(df, ignore_index=True)
                df.set_index('name', inplace=True)
                st.dataframe(df, use_container_width=True)

            c1, c2 = st.columns(2)
            b1 = c1.button('Add', use_container_width=True, on_click=add)
            b2 = c2.button('Delete', use_container_width=True, on_click=delete,
                           disabled=len(st.session_state['trials']) == 0, type='primary')