import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
from streamlit_molstar import st_molstar_content
from itertools import tee
import time


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


def get_table(path, key=None):
    if key is None:
        return pd.DataFrame(columns=['chain', 'min_len', 'max_len'])
    config = get_config(path)
    p = Path(path).parent / config['diffusion'][key]
    return pd.read_csv(p)


def init():
    if 'trials' not in st.session_state:
        st.session_state['trials'] = []
    if 'wkdir' not in st.session_state:
        st.session_state['wkdir'] = ''


def validate_dir(d):
    return d and Path(d).is_dir()


def get_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def put_config(c, path):
    with open(path, 'w') as f:
        f.write(yaml.dump(c))


def post_process_mpnn(path):
    with open(path, 'r') as f:
        text = '>' + f.read().split('>')[1]
        text = text.replace('/', ':')
    with open(path, 'w') as f:
        f.write(text)


@st.fragment
def visual(pdb_list):
    choice = st.selectbox('Select a result', pdb_list)
    if choice is not None:
        with open(choice, 'r') as f:
            pdb = f.read()
        st_molstar_content(pdb, 'pdb', height='500px')


def progress(process, tot, msg, glob):
    bar = st.progress(0, msg)
    while process.poll() is None:
        output_pdbs = [*tee(glob, 1)[0]]
        bar.progress(len(output_pdbs) / tot, msg)
        time.sleep(0.5)
    time.sleep(1)
    bar.empty()
