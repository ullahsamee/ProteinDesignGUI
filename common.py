import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
from streamlit_molstar import st_molstar_content
import time
import json


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


def reset_proc():
    if process_ongoing():
        st.session_state['process'].terminate()
        return True
    return False


def abort_proc():
    if reset_proc():
        st.toast('Job aborted', icon="🛑")


def validate_dir(d):
    return d and Path(d).is_dir()


def get_config(path=None):
    if path is None:
        with open('default.json', 'r') as f:
            return json.load(f)
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def put_config(c, path):
    with open(path, 'w') as f:
        f.write(yaml.dump(c))


@st.fragment
def visual(pdb_list):
    choice = st.selectbox('Select a result', pdb_list)
    if choice is not None:
        with open(choice, 'r') as f:
            pdb = f.read()
        st_molstar_content(pdb, 'pdb', height='500px')


def progress():
    state = st.session_state
    placeholder = st.sidebar.container()
    tot, msg, outdir, wildcard, stage, trial = state['process_args']
    bar = placeholder.progress(0, msg)
    while state['process'].poll() is None:
        pro = len([*outdir.glob(wildcard)])
        bar.progress(pro / tot, msg + f' ({pro}/{tot})')
        time.sleep(0.5)
    bar.empty()
    if state['process'].returncode == 0:
        placeholder.success('Trial complete!', icon="✅")
    else:
        placeholder.error('Trial Unfinished.', icon="⛔")

    state['auto'] = trial
    if stage == 1 and state['proceed1']:
        st.switch_page('mpnn.py')
    elif stage == 2 and state['proceed2']:
        method = get_config(trial)['qc']['fold']
        if method == 2:
            st.switch_page('page_files/colabfold.py')
        else:
            st.switch_page('page_files/boltz.py')
    elif stage == 3 and state['proceed3']:
        st.switch_page('page_files/qc.py')
    else:
        state['auto'] = None


def extract_chains(pdb):
    chains = set()  # Use a set to avoid duplicate chain identifiers
    with open(pdb, 'r') as f:
        for line in f.readlines():
            if line.startswith(("ATOM", "HETATM")):
                chain_id = line[21].strip()  # Chain ID is in column 22 (index 21 in Python)
                if chain_id:
                    chains.add(chain_id)
    return sorted(chains)


def table_update(origin, updates):
    data = pd.DataFrame(origin, dtype=str)
    data['min_len'] = data['min_len'].astype(int)
    data['max_len'] = data['max_len'].astype(int)
    for ind, row in updates['edited_rows'].items():
        for k, v in row.items():
            data.loc[ind, k] = v
    data.drop(updates['deleted_rows'], inplace=True)
    for row in updates['added_rows']:
        data = pd.concat([data, pd.DataFrame([row])], axis=0)
    return data.to_dict('list')


def table_edit(data, pdb, key):
    ops = extract_chains(pdb) if pdb is not None else [*(chr(i) for i in range(ord('A'), ord('Z') + 1))]
    data = pd.DataFrame(data, dtype=str)
    data['min_len'] = data['min_len'].astype(int)
    data['max_len'] = data['max_len'].astype(int)
    st.data_editor(
        data, column_order=['chain', 'min_len', 'max_len'], num_rows='dynamic', use_container_width=True, key=key,
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain', options=ops, required=pdb is None),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )


def process_ongoing():
    return st.session_state['process'] is not None and st.session_state['process'].poll() is None
