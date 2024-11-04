import pandas as pd
import streamlit as st
from tempfile import TemporaryDirectory
from pathlib import Path
import subprocess
import time
import zipfile
from streamlit_molstar import st_molstar_content
import io
import yaml


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


def convert_selection(df):
    sel = '['
    for ind, row in df.iterrows():
        a = int(row['min_len'])
        b = int(row['max_len'])
        if row['chain'] is None or pd.isna(row['chain']):
            if a == b == 0:
                sel += '0 '
            else:
                sel += f'{a}-{b}/'
        else:
            sel += f"{row['chain']}{a}-{b}/"
    sel = sel.rstrip(' /') + ']'
    return sel


@st.fragment
def table_edit(data, key):
    table = st.data_editor(
        data, column_order=None, num_rows='dynamic', use_container_width=True, key=f'{key}.data',
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain',
                                                      options=[*(chr(i) for i in range(ord('A'), ord('Z') + 1))],
                                                      required=False),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )
    st.session_state[key] = convert_selection(table)
    st.markdown(f'The specified sequence map: `{st.session_state[key]}`')


if __name__ == '__main__':
    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"{config['PATH']['RFdiffusion']}/scripts/run_inference.py"
    st.set_page_config('Protein Design: Motif Scaffolding', layout='wide')
    st.title('Motif Scaffolding')
    tab1, tab2 = st.tabs(['Interactive', 'Batch'])

    with tab2:
        st.header('Batch Mode')
        with st.form('path', border=False):
            c1, c2 = st.columns([3, 1], vertical_alignment='bottom')
            root = c1.text_input('Root directory for input batches')
            clicked2 = c2.form_submit_button('Scan Directory', use_container_width=True)
        if clicked2:
            folders = []
            for i in Path(root).glob('*'):
                if not i.is_dir():
                    continue
                if not (i / 'contig.csv').exists():
                    continue
                temp = list(i.glob('*.pdb'))
                if len(temp) != 1:
                    continue
                folders.append(i)
                st.write(i)
            if folders:
                placeholder = st.empty()
                with placeholder.container():
                    st.write(folders)
                    clicked1 = placeholder.button(f'Run batch inference', use_container_width=True, type='primary')
                if clicked1:
                    placeholder.empty()
                    for i, folder in enumerate(folders):
                        try:
                            config = yaml.safe_load(list(folder.glob('*.yml'))[0])
                            n_design = config['n_design']
                            n_T = config['n_timestamp']
                            pdb = list(folder.glob('*.pdb'))[0]
                            contig = pd.read_csv(folder / 'contig.csv', usecols=['chain', 'min_len', 'max_len'])
                            contig = convert_selection(contig)
                            if inpaint.exists():
                                inpaint = pd.read_csv(folder / 'inpaint.csv', usecols=['chain', 'min_len', 'max_len'])
                                inpaint = convert_selection(inpaint)
                            else:
                                inpaint = None

                            cmd = f"""
                            cd {folder}
                            python {exe} inference.output_prefix=results/design inference.input_pdb={pdb}"""
                            cmd += f" 'contigmap.contigs={contig}' inference.num_designs={n_design} diffuser.T={n_T}"
                            if inpaint is not None:
                                cmd += f" 'contigmap.inpaint_seq={inpaint}'"
                            process = subprocess.Popen(['/bin/bash', '-c', cmd])
                            msg = f'Running inference.. ({i}/{len(folders)})'
                            bar = st.progress(0, msg)
                            while process.poll() is None:
                                output_pdbs = sorted((folder / 'results').glob('*.pdb'))
                                bar.progress(len(output_pdbs) / n_design, msg)
                                time.sleep(0.5)
                            time.sleep(1)
                            bar.empty()
                        except Exception as e:
                            st.write(e)

    with tab1:
        st.header('Interactive Mode')
        pdb = st.file_uploader('Input a PDB to for motif reference', '.pdb')
        if pdb is not None:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    n_design = st.number_input('Number of designs', 1, value=100, step=10, format='%d')
                    st.subheader('Contigs Setting')
                    file = st.file_uploader('Upload a CSV or edit in the table below', '.csv',
                                            key=f'contigs.uploader')
                    table1 = pd.DataFrame(
                        {
                            'chain': ['A', None, 'L', None],
                            'min_len': [54, 0, 40, 20],
                            'max_len': [74, 0, 50, 20],
                        }
                    ) if file is None else pd.read_csv(file)
                    table_edit(table1, 'contig')
                with col2:
                    n_T = st.number_input('Number of timestamps', 15, value=50, step=10, format='%d')
                    st.subheader('Inpaint Setting')
                    file = st.file_uploader('Upload a CSV or edit in the table below', '.csv', key=f'inpaint.uploader')
                    table2 = pd.DataFrame(columns=['chain', 'min_len', 'max_len']) if file is None else pd.read_csv(file)
                    table_edit(table2, 'inpaint')

                clicked = st.button('Run Inference!', use_container_width=True, disabled=len(st.session_state['contig']) < 3 or pdb is None,
                                    type='primary')

            if clicked:
                with TemporaryDirectory() as tdir:
                    tdir = Path(tdir)
                    temp_pdb = tdir / 'input.pdb'
                    with open(temp_pdb, 'wb') as f:
                        f.write(pdb.getvalue())
                    cmd = f"""
                    cd {tdir}
                    python {config['PATH']['RFdiffusion']}/scripts/run_inference.py inference.output_prefix=res/design inference.input_pdb={temp_pdb}"""
                    cmd += f" 'contigmap.contigs={st.session_state['contig']}' inference.num_designs={n_design} diffuser.T={n_T}"
                    if len(st.session_state['inpaint']) > 2:
                        cmd += f" 'contigmap.inpaint_seq={st.session_state['inpaint']}'"
                    process = subprocess.Popen(['/bin/bash', '-c', cmd])
                    bar = st.progress(0, f'Running inference.. ({0}/{n_design})')
                    while process.poll() is None:
                        output_pdbs = sorted((tdir / 'res').glob('*.pdb'))
                        bar.progress(len(output_pdbs) / n_design, f'Running inference.. ({len(output_pdbs)}/{n_design})')
                        time.sleep(0.5)
                    time.sleep(1)
                    bar.empty()
                    st.session_state['results'] = {}
                    for i in output_pdbs:
                        with open(i, 'r') as f:
                            st.session_state['results'][i.name] = f.read()
                    zio = zip_files(output_pdbs)
                    show()
