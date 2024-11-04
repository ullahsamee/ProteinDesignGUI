import streamlit as st
import yaml
from tempfile import TemporaryDirectory
from pathlib import Path
import subprocess
import time
from streamlit_molstar import st_molstar_content
import io
import zipfile


@st.fragment
def show():
    st.header('Results')
    choice = st.selectbox('Visualize your results', st.session_state['results'].keys())
    st_molstar_content(st.session_state['results'][choice], 'pdb', height='500px')
    st.download_button('Download result PDBs', zio, 'motif_scaffolding_results.zip')


def zip_files(file_paths):
    # Create a BytesIO object
    zip_buffer = io.BytesIO()

    # Create a zip file in the BytesIO buffer
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            # Add each file to the zip
            zip_file.write(file_path, arcname=str(file_path).split('/')[-1])  # Use only the filename in the zip

    # Seek to the beginning of the BytesIO object
    zip_buffer.seek(0)

    return zip_buffer


def ops(key):
    with st.form('ops'):
        c1 = st.checkbox('Use amber', key=f'{key}.c1')
        c2 = st.checkbox('Use template', key=f'{key}.c2')
        nmod = st.selectbox('Number of models', [1, 2, 3, 4, 5], 4)
        n_recycle = st.number_input('Number of recycle', 1, value=3, key=f'{key}.n')
        clicked = st.form_submit_button('Run Structure Prediction', type='primary', use_container_width=True)
    return c1, c2, nmod, n_recycle, clicked


if __name__ == '__main__':
    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"{config['PATH']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    st.set_page_config('Protein Design: Local ColabFold')
    st.title('Local ColabFold')
    tab1, tab2 = st.tabs(['Interactive', 'Batch'])

    with tab1:
        st.header('Interactive Mode')
        fa = st.file_uploader('Upload protein sequences', '.fasta')
        if fa is not None:
            amber, template, nmod, n_recycle, clicked = ops('tab1')
            if clicked:
                with TemporaryDirectory() as tdir:
                    tdir = Path(tdir)
                    tempfa = tdir / fa.name
                    outdir = tdir / "results"
                    with open(tempfa, 'wb') as f:
                        f.write(fa.getvalue())
                    cmd = exe
                    if amber:
                        cmd += ' --amber'
                    if template:
                        cmd += ' --templates'
                    cmd += f' --num-models {nmod} {tempfa} {outdir}'
                    process = subprocess.Popen(['/bin/bash', '-c', cmd])
                    bar = st.progress(0, f'Running prediction.. ({0}/{nmod + 1})')
                    while process.poll() is None:
                        output_pdbs = sorted(outdir.glob('*.pdb'))
                        bar.progress(len(output_pdbs) / (nmod + 1),
                                     f'Running prediction.. ({len(output_pdbs)}/{nmod + 1})')
                        time.sleep(0.5)
                    time.sleep(1)
                    bar.empty()
                    st.session_state['results'] = {}
                    for i in output_pdbs:
                        with open(i, 'r') as f:
                            st.session_state['results'][i.name] = f.read()
                    zio = zip_files(output_pdbs)
                    show()

    with tab2:
        st.header('Batch Mode')
        with st.form('path', border=False):
            c1, c2 = st.columns([3, 1], vertical_alignment='bottom')
            root = c1.text_input('Root directory for protein sequences')
            clicked2 = c2.form_submit_button('Scan Directory', use_container_width=True)
        if clicked2:
            fa = list(Path(root).rglob('*.fasta'))
            if fa:
                placeholder = st.empty()
                placeholder.write(fa)
                amber, template, nmod, n_recycle, clicked = ops('tab2')
                if clicked:
                    placeholder.empty()
                    for i, a in enumerate(fa):
                        try:
                            outdir = a.parent / a.stem
                            cmd = exe
                            if amber:
                                cmd += ' --amber'
                            if template:
                                cmd += ' --templates'
                            cmd += f' --num-models {nmod} {a} {outdir}'
                            process = subprocess.Popen(['/bin/bash', '-c', cmd])
                            bar = st.progress(0, f'Running prediction.. ({0}/{nmod + 1})')
                            while process.poll() is None:
                                output_pdbs = sorted(outdir.glob('*.pdb'))
                                bar.progress(len(output_pdbs) / (nmod + 1),
                                             f'Running prediction.. ({len(output_pdbs)}/{nmod + 1})')
                                time.sleep(0.5)
                            time.sleep(1)
                            bar.empty()
                        except Exception as e:
                            st.write(e)
