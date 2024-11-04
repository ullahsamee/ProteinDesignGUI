import streamlit as st
import yaml
from tempfile import TemporaryDirectory
from pathlib import Path
import subprocess
import time
import io
import zipfile



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


def ops(key, chains=None):
    with st.form('ops'):
        n1 = st.number_input('seq/chain', 1, None, 2, key=f'{key}.n1')
        ops = chains if chains is not None else [*(chr(i) for i in range(ord('A'), ord('Z') + 1))]
        m1 = st.multiselect('chains to design', ops, chains, key=f'{key}.m1')
        n2 = st.number_input('temperature', 0., 1., 0.1, key=f'{key}.n2')
        clicked = st.form_submit_button('Run Structure Prediction', type='primary', use_container_width=True)
    return n1, m1, n2, clicked


def extract_chains(pdb_file):
    chains = set()  # Use a set to avoid duplicate chain identifiers
    for line in pdb_file:
        if line.startswith(("ATOM", "HETATM")):
            chain_id = line[21].strip()  # Chain ID is in column 22 (index 21 in Python)
            if chain_id:
                chains.add(chain_id)
    return sorted(chains)


@st.fragment
def show():
    st.header('Results')
    st.write(st.session_state['results'])
    st.download_button('Download result FASTA', st.session_state['results'], output.name)


if __name__ == '__main__':
    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"python {config['PATH']['ProteinMPNN']}/protein_mpnn_run.py"
    st.set_page_config('Protein Design: ProteinMPNN')
    st.title('ProteinMPNN')
    tab1, tab2 = st.tabs(['Interactive', 'Batch'])

    with tab1:
        st.header('Interactive Mode')
        pdb = st.file_uploader('Upload protein sequences', '.pdb')
        if pdb is not None:
            txt = pdb.getvalue()
            n_seq, chains, temp, clicked = ops('tab1', extract_chains(txt))
            if clicked:
                with TemporaryDirectory() as tdir:
                    tdir = Path(tdir)
                    temppdb = tdir / pdb.name
                    outdir = tdir / "results"
                    chains = ' '.join(chains)
                    with open(temppdb, 'wb') as f:
                        f.write(txt)
                    cmd = exe + f' --pdb_path {temppdb} --pdb_path_chains "{chains}" --out_folder {outdir}'
                    cmd += f' --num_seq_per_target {n_seq} --sampling_temp "{temp}"'
                    with st.spinner('Predicting sequence..'):
                        subprocess.run(['/bin/bash', '-c', cmd])
                    output = list(outdir.glob('*.fasta'))[0]
                    with open(output, 'r') as f:
                        st.session_state['results'] = f.read()
                    show()

    with tab2:
        st.header('Batch Mode')
        with st.form('path', border=False):
            c1, c2 = st.columns([3, 1], vertical_alignment='bottom')
            root = c1.text_input('Root directory for protein sequences')
            clicked2 = c2.form_submit_button('Scan Directory', use_container_width=True)
        if clicked2:
            pdb = list(Path(root).rglob('*.pdb'))
            if pdb:
                placeholder = st.empty()
                placeholder.write(pdb)
                n_seq, chains, temp, clicked = ops('tab1', extract_chains(txt))
                if clicked:
                    placeholder.empty()
                    bar = st.progress(0, f'Running prediction.. ({0}/{len(pdb)})')
                    for i, a in enumerate(pdb):
                        try:
                            outdir = a.parent / a.stem
                            chains = ' '.join(chains)
                            cmd = exe + f' --pdb_path {a} --out_folder {outdir}'
                            if len(chains) > 0:
                                cmd += f' --pdb_path_chains "{chains}"'
                            cmd += f' --num_seq_per_target {n_seq} --sampling_temp "{temp}"'
                            subprocess.run(['/bin/bash', '-c', cmd])
                            bar.progress(i + 1 / len(pdb), f'Predicting sequence.. ({i + 1}/{len(pdb)})')
                            output = list(outdir.glob('*.fasta'))[0]
                            bar.empty()
                        except Exception as e:
                            st.write(e)
