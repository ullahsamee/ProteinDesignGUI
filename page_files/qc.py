import pandas as pd

from common import *
from Bio.PDB import PDBParser
from Bio.PDB.cealign import CEAligner
import json
from Bio import SeqIO


state = st.session_state


def sync(config):
    config['win_size']  = state['win_size']
    config['max_gap'] = state['max_gap']
    config['fold'] = state['fold']


def save():
    sync(cfg['qc'])
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def extract_fname(fname, field):
    fname = fname.split(f'_{field}')[-1]
    return fname[:fname.find('_')]


def get_error(path: Path, dname):
    sample_num = extract_fname(path.name, 'Sample')
    data = next((path.parent / dname).glob(f'*_sample_{sample_num}_*scores*.json'))
    with open(data, 'r') as f:
        data = json.load(f)
    return data['max_pae'], data['ptm']


def get_error2(path: Path):
    model_num = extract_fname(path.name, 'model')
    prefix = '_'.join(path.stem.split('_')[:2])
    data = next((path.parent / 'predictions').glob(f'{prefix}*/confidence_{prefix}*_{model_num}.json'))
    with open(data, 'r') as f:
        data = json.load(f)
    return data['confidence_score'], data['ptm'], data['complex_plddt']

def run(trial):
    cfg = get_config(trial)
    config = cfg['qc']
    p, a = PDBParser(), CEAligner(config['win_size'], config['max_gap'])
    table = []
    for i in (trial.parent / indir1).glob('*.fasta'):
        a.set_reference(p.get_structure('a', trial.parent / indir3 / i.with_suffix('.pdb').name))
        for record in SeqIO.parse(i, "fasta"):
            metadata = record.description.split(", ")
            metadata_dict = {item.split("=")[0]: item.split("=")[1] for item in metadata if "=" in item}
            name = i.stem
            if name.startswith('design_'):
                name = f'Design{name[7:]}'
            for mod in (trial.parent / f'AF{config["fold"]}').glob(f'{name}_Sample{metadata_dict["sample"]}_*.pdb'):
                a.align(p.get_structure('b', mod), False)
                if config['fold'] == 2:
                    pae, ptm = get_error(mod, i.stem)
                    table.append({
                        'filename': mod.stem,
                        'sequence': str(record.seq),
                        'RMSD': a.rms,
                        'max PAE': pae,
                        'pTM': ptm
                    })
                else:
                    conf, ptm, plddt = get_error2(mod)
                    table.append({
                        'filename': mod.stem,
                        'sequence': str(record.seq),
                        'RMSD': a.rms,
                        'conf': conf,
                        'pTM': ptm,
                        'plddt': plddt
                    })
    if config['fold'] == 2:
        table = pd.DataFrame(table, columns=['filename', 'sequence', 'RMSD', 'max PAE', 'pTM'])
    else:
        table = pd.DataFrame(table, columns=['filename', 'sequence', 'RMSD', 'plddt', 'pTM'])
    table.to_csv(trial.parent / f'AF{config["fold"]}_qc.csv', index=False)
    st.dataframe(table, hide_index=True, use_container_width=True, column_config={
        "sequence": st.column_config.TextColumn(width='medium')
    })


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    indir1 = 'seqs'
    indir3 = 'diffusion'

    st.title('Quality Control')
    tab1, = st.tabs(['Configure'])
    if active is not None:
        active = Path(active)

    cfg = get_config(active)
    config = cfg['qc']
    with tab1:
        with st.form('form'):
            col1, col2, col3 = st.columns(3)
            col1.number_input('Window size', 1, value=config['win_size'], key='win_size')
            col2.number_input('Max gap', 0, value=config['max_gap'], key='max_gap')
            ops = [2, 3]
            col3.selectbox('AlphaFold version', ops, ops.index(config['fold']), key='fold')
            col1, col2 = st.columns(2)
            col1.form_submit_button('SAVE', use_container_width=True, on_click=save, disabled=active is None)
            clicked = col2.form_submit_button('COMPUTE', use_container_width=True, on_click=save, disabled=active is None,
                                              type='primary')

    if state['auto'] is not None:
        run(state['auto'])
        state['auto'] = None
    elif clicked:
        run(active)

    if process_ongoing():
        progress()