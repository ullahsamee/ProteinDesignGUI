import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
from streamlit_molstar import st_molstar_content
import time
import numpy as np


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


def stop_proc():
    if st.session_state['process'] is not None:
        st.session_state['process'].terminate()
        if st.session_state['batch_progress'] >= 0:
            st.session_state['batch_progress'] = np.inf


def init():
    if 'trials' not in st.session_state:
        st.session_state['trials'] = []
    if 'wkdir' not in st.session_state:
        st.session_state['wkdir'] = ''
    if 'process' not in st.session_state:
        st.session_state['process'] = None
    if 'batch_progress' not in st.session_state:
        st.session_state['batch_progress'] = -1
    if 'process_type' not in st.session_state:
        st.session_state['process_type'] = ''
    st.sidebar.button('Stop Process', on_click=stop_proc, type='primary', use_container_width=True)


def validate_dir(d):
    return d and Path(d).is_dir()


def get_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def put_config(c, path):
    with open(path, 'w') as f:
        f.write(yaml.dump(c))


def get_score(seq):
    f1 = seq.find(' score=') + 7
    f2 = seq.find(',', f1)
    return float(seq[f1:f2])


def post_process_mpnn(path, topN):
    with open(path, 'r') as f:
        seqs = f.read().split('>')[2:]
        scores = [get_score(s) for s in seqs]
        seqs = [seqs[i] for i in np.argsort(scores)[:min(len(seqs), topN)]]
        text = '>' + '>'.join(seqs).replace('/', ':')
    with open(path.with_suffix('.fasta'), 'w') as f:
        f.write(text)


def get_table(path, key1, key2):
    cfg = get_config(path)
    return pd.read_csv(path.parent / cfg[key1][key2], usecols=['chain', 'min_len', 'max_len'])


@st.fragment
def visual(pdb_list):
    choice = st.selectbox('Select a result', pdb_list)
    if choice is not None:
        with open(choice, 'r') as f:
            pdb = f.read()
        st_molstar_content(pdb, 'pdb', height='500px')


def progress():
    tot, msg, wkdir, prefix = st.session_state['process_args']
    bar = st.progress(0, msg)
    while st.session_state['process'].poll() is None:
        output_pdbs = [*wkdir.glob(f'{prefix}*.pdb')]
        bar.progress(len(output_pdbs) / tot, msg)
        time.sleep(0.5)
    time.sleep(1)
    bar.empty()


def extract_chains(pdb):
    chains = set()  # Use a set to avoid duplicate chain identifiers
    with open(pdb, 'r') as f:
        for line in f.readlines():
            if line.startswith(("ATOM", "HETATM")):
                chain_id = line[21].strip()  # Chain ID is in column 22 (index 21 in Python)
                if chain_id:
                    chains.add(chain_id)
    return sorted(chains)


@st.fragment
def table_edit(data, pdb, key):
    ops = extract_chains(pdb) if pdb is not None else [*(chr(i) for i in range(ord('A'), ord('Z') + 1))]
    table = st.data_editor(
        data, column_order=None, num_rows='dynamic', use_container_width=True, key=f'{key}.data',
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain', options=ops, required=pdb is None),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )
    st.session_state[key] = table
    st.markdown(f'The specified sequence map: `{convert_selection(st.session_state[key])}`')


def process_ongoing():
    return st.session_state['process'] is not None and st.session_state['process'].poll() is None
