import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
from streamlit_molstar import st_molstar_content
import time
import numpy as np
import shutil
import subprocess


def convert_selection(df):
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df, dtype=str)
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
    state = st.session_state
    if 'trials' not in state:
        state['trials'] = []
    if 'wkdir' not in state:
        state['wkdir'] = ''
    if 'process' not in state:
        state['process'] = None
    if 'batch_progress' not in state:
        state['batch_progress'] = -1
    if 'process_type' not in state:
        state['process_type'] = ''
    if 'proceed1' not in state:
        state['proceed1'] = False
    if 'proceed2' not in state:
        state['proceed2'] = False

    def select_batch():
        st.session_state['current_batch']()

    st.sidebar.button('Batch Run', on_click=select_batch, use_container_width=True,
                      disabled=state['current_batch'] is None)
    st.sidebar.subheader('Batch Automation')

    def toggle1():
        state['proceed1'] = state['toggle1']

    def toggle2():
        state['proceed2'] = state['toggle2']

    st.sidebar.toggle('Proceed after RFDiffusion', state['proceed1'], key='toggle1', on_change=toggle1)
    st.sidebar.toggle('Proceed after ProteinMPNN', state['proceed2'], key='toggle2', on_change=toggle2)
    st.sidebar.divider()
    st.sidebar.button('Abort Process', on_click=stop_proc, type='primary', use_container_width=True)
    return st.sidebar.empty()


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


@st.fragment
def visual(pdb_list):
    choice = st.selectbox('Select a result', pdb_list)
    if choice is not None:
        with open(choice, 'r') as f:
            pdb = f.read()
        st_molstar_content(pdb, 'pdb', height='500px')


def progress(placeholder):
    tot, msg, wkdir, prefix = st.session_state['process_args']
    bar = placeholder.progress(0, msg)
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


def table_edit(data, pdb, key):
    ops = extract_chains(pdb) if pdb is not None else [*(chr(i) for i in range(ord('A'), ord('Z') + 1))]
    data = pd.DataFrame(data, dtype=str)
    data['min_len'] = data['min_len'].astype(int)
    data['max_len'] = data['max_len'].astype(int)
    data = st.data_editor(
        data, column_order=['chain', 'min_len', 'max_len'], num_rows='dynamic',
        use_container_width=True, key=f'{key}.data',
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain', options=ops, required=pdb is None),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )
    data['min_len'] = data['min_len'].astype(int)
    data['max_len'] = data['max_len'].astype(int)
    # st.markdown(f'The specified sequence map: `{convert_selection(data)}`')
    st.session_state[key] = data


def process_ongoing():
    return st.session_state['process'] is not None and st.session_state['process'].poll() is None


def signify_complete(placeholder):
    if st.session_state['process'].returncode == 0:
        placeholder.success('Trial complete!', icon="✅")
    else:
        placeholder.error('Trial terminated.', icon="⛔")


def signify_batch_complete(placeholder):
    if np.isinf(st.session_state['batch_progress']):
        placeholder.error('Batch aborted', icon="⛔")
    else:
        placeholder.success(f'Batch complete!', icon="✅")