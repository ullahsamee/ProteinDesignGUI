from common import *
import configparser
from Bio.PDB import PDBParser
from Bio.PDB.cealign import CEAligner
import json
from Bio import SeqIO


state = st.session_state


def sync(config):
    config['win_size']  = state['win_size']
    config['max_gap'] = state['max_gap']
    config['protein'] = state['protein'].name


def save():
    sync(cfg)
    with open(active.parent / refdir / cfg['qc']['protein'], 'wb') as f:
        f.write(config['protein'].getvalue())
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def extract_fname(fname):
    f1 = fname.find('Sample') + 6
    f2 = fname.find('_', f1)
    return fname[f1:f2], fname[:fname.find('_')]


def get_error(path: Path):
    sample_num, dname = extract_fname(path.name)
    data = next((path.parent / dname).glob(f'_sample_{sample_num}_*.json'))
    with open(data, 'r') as f:
        data = json.load(f)
    return data['max_pae'], data['ptm']


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    refdir = 'qc_input'
    indir1 = 'mpnn'
    indir2 = 'fold'

    config = configparser.ConfigParser()

    st.title('Quality Control')
    tab1, = st.tabs(['Configure'])
    if active is not None:
        active = Path(active)

    cfg = get_config(active)
    config = cfg['qc']
    with tab1:
        with st.form('form'):
            st.file_uploader('Upload a PDB as a reference protein', '.pdb', False, key='protein')
            st.write('**Saved Reference Protein:**', config['protein'])
            col1, col2 = st.columns(2)
            ws = col1.number_input('Window size', .01, value=float(config['win_size']), key='win_size')
            mg = col2.number_input('Max gap', 0., value=float(config['max_gap']), key='max_gap')
            col1.form_submit_button('Save', use_container_width=True, on_click=save, disabled=active is None)
            clicked = col2.form_submit_button('Calculate', use_container_width=True, on_click=save, disabled=active is None)

    if clicked:
        p, a = PDBParser(), CEAligner()
        a.set_reference(p.get_structure('a', active.parent / refdir / config['protein']))
        table = []
        for i in (active.parent / indir1).glob('*.fasta'):
            for record in SeqIO.parse(i, "fasta"):
                # Parse the header metadata
                metadata = record.description.split(", ")
                metadata_dict = {item.split("=")[0]: item.split("=")[1] for item in metadata if "=" in item}
                for mod in (active.parent / indir2).glob(f'{i.name}_Sample{metadata_dict["sample"]}_*.pdb'):
                    pae, ptm = get_error(mod)
                    table.append({
                        'filename': mod.name,
                        'sequence': record.seq,
                        'RMSD': a.align(p.get_structure('b', mod), False),
                        'PAE': pae,
                        'pTM': ptm
                    })
        table = pd.DataFrame(table, columns=['filename', 'sequence', 'RMSD', 'PAE', 'pTM'])
        table.to_csv(active.parent / 'qc.csv')
        st.dataframe(table)

    if process_ongoing():
        progress()