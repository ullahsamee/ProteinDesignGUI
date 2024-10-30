import streamlit as st
import yaml
from tempfile import TemporaryDirectory
from pathlib import Path


def ops(key):
    with st.form('ops'):
        c1 = st.checkbox('Use amber', key=f'{key}.c1')
        c2 = st.checkbox('Use template', key=f'{key}.c2')
        n_recycle = st.number_input('Number of recycle', 1, value=3, key=f'{key}.n')
        clicked = st.form_submit_button('Run', type='primary', use_container_width=True)
        return c1, c2, n_recycle, clicked

if __name__ == '__main__':
    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"{config['PATH']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    st.set_page_config('Protein Design: Local ColabFold')
    st.title('Local ColabFold')
    tab1, tab2 = st.tabs(['Batch', 'Interactive'])
    with tab1:
        files = st.file_uploader('Upload protein structures', '.pdb', accept_multiple_files=True)
        if not files:
            amber, template, n_recycle, clicked = ops('tab1')
            if clicked:
                with TemporaryDirectory() as tdir:
                    tdir = Path(tdir)
                    for i in files:
                        cmd = exe
                        if amber:
                            cmd += ' --amber'
                        if template:
                            cmd += ' --templates'

