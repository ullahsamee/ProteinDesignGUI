import pandas as pd
import streamlit as st
from tempfile import TemporaryDirectory
from pathlib import Path
import subprocess
import time
import zipfile


def zip_files(files, output_zip):
    """Zips the given list of files into output_zip."""

    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for file in files:
            # Add each file to the zip archive
            zipf.write(file, file.name)


def contig_upload_edit(parent, table, key):
    file = parent.file_uploader('Upload a CSV or edit in the table below', '.csv',
                                key=f'{key}.uploader')
    if file is not None:
        st.session_state[table] = pd.read_csv(file)

    st.session_state[table] = parent.data_editor(
        st.session_state[table], column_order=None, num_rows='dynamic', use_container_width=True, key=f'{key}.editor',
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain',
                                                      options=[*(chr(i) for i in range(ord('A'), ord('Z') + 1))],
                                                      required=False),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )
    sel = '['
    for ind, row in st.session_state[table].iterrows():
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

    parent.markdown(f'The specified sequence map: `{sel}`')

    return sel


if __name__ == '__main__':
    if 'contig_table' not in st.session_state:
        st.session_state['contig_table'] = pd.DataFrame(
                {
                    'chain': ['A', None, 'B', None],
                    'min_len': [20, 0, 40, 100],
                    'max_len': [100, 0, 50, 100],
                }
            )
    if 'inpaint_table' not in st.session_state:
        st.session_state['inpaint_table'] = pd.DataFrame(columns=['chain', 'min_len', 'max_len'])
    st.set_page_config('Protein Design: Motif Scaffolding', layout='wide')
    st.title('Motif Scaffolding')
    st.divider()
    st.header('Input Params')
    with st.container(border=True):
        col1, col2 = st.columns(2)
        n_design = col1.number_input('Number of designs', 1, value=100, step=10, format='%d')
        n_T = col1.number_input('Number of timestamps', 15, value=50, step=10, format='%d')
        pdb = col2.file_uploader('Input a PDB to for motif reference (optional)', '.pdb')

        select_cols = st.columns(2)
        select_cols[0].subheader('Contigs Setting')
        sel1 = contig_upload_edit(select_cols[0], 'contig_table', 'contigs')
        select_cols[1].subheader('Inpaint Setting')
        sel2 = contig_upload_edit(select_cols[1], 'inpaint_table', 'inpaint')
        clicked = st.button('Run Inference!', use_container_width=True, disabled=len(sel1) < 3 or pdb is None,
                            type='primary')

    if clicked:
        st.header('Results')
        with TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            temp_pdb = tdir / '.pdb'
            with open(temp_pdb, 'wb') as f:
                f.write(pdb.getvalue())
            cmd = f"""
            cd {tdir}
            source /opt/anaconda3/etc/profile.d/conda.sh
            conda activate SE3nv
            python $HOME/RFdiffusion/scripts/run_inference.py inference.output_prefix=res inference.input_pdb={temp_pdb}"""
            cmd += f' contigmap.contigs={sel1} inference.num_designs={n_design} diffuser.T={n_T}'
            if len(sel2) > 2:
                cmd += f" 'contigmap.inpaint_seq={sel2}'"
            st.text(cmd)
            process = subprocess.Popen(cmd, shell=True)
            bar = st.progress(0, 'Running inference..')
            while process.poll() is None:
                output_pdbs = list(tdir.glob('*.pdb'))
                bar.progress(len(output_pdbs) / n_design)
                time.sleep(0.5)
            time.sleep(1)
            bar.empty()
            output_zip = tdir / 'out.zip'
            zip_files(output_pdbs, output_zip)
            with open(output_zip, 'rb') as f:
                st.download_button('Download result PDBs', f)
