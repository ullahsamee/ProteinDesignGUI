from common import *
import configparser
import shutil
import subprocess
from os.path import expandvars
from datetime import datetime


state = st.session_state


@st.dialog('Try with uploading a protein structure')
def try_run():
    pdb = st.file_uploader('Input a PDB for motif reference', '.pdb')
    if st.button('Confirm', use_container_width=True):
        assert pdb is not None, 'No PDB uploaded.'
        cache_dir = cache / f'{datetime.now()} motif_scaffolding'
        input_dir = cache_dir / indir
        input_dir.mkdir(parents=True, exist_ok=True)
        t = cache_dir / 'config.yml'
        cfg = get_config(active)
        cfg['diffusion']['protein'] = pdb.name
        sync(cfg['diffusion'])
        cfg['name'] = 'TestJob'
        put_config(cfg, t)
        with open(input_dir / pdb.name, 'wb') as f:
            f.write(pdb.getvalue())
        setup_process(t)
        st.rerun()


def get_cmd(wkdir, protein, contig, inpaint, n_design, n_timestamp, beta):
    cmd = f"""
    cd "{wkdir}"
    {exe} inference.output_prefix={prefix} inference.input_pdb={indir}/{protein} \
    'contigmap.contigs={convert_selection(contig)}' inference.num_designs={n_design} diffuser.T={n_timestamp} \
    {'inference.ckpt_override_path=models/Complex_beta_ckpt.pt' if beta else ''}
    """
    temp = convert_selection(inpaint)
    if len(temp) > 2:
        cmd += f" 'contigmap.inpaint_seq={temp}'"
    return cmd


def sync(config):
    config['n_design'] = state['n_design']
    config['beta'] = state['beta']
    config['n_timestamp'] = state['n_timestamp']
    config['contig'] = table_update(config['contig'], state['contig'])
    config['inpaint'] = table_update(config['inpaint'], state['inpaint'])


def save():
    sync(cfg['diffusion'])
    d = active.parent / indir
    d.mkdir(parents=True, exist_ok=True)
    if state['protein'] is not None:
        config['protein'] = state['protein'].name
        with open(d / cfg['diffusion']['protein'], 'wb') as f:
            f.write(state['protein'].getvalue())
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def setup_process(trial):
    p = trial.parent
    o = p / outdir
    cfg = get_config(trial)
    state['auto'] = None
    shutil.rmtree(o, ignore_errors=True)
    cmd = get_cmd(p, **cfg['diffusion'])
    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
    state['process_args'] = cfg['diffusion']['n_design'], f'Motif scaffolding for {cfg["name"]}..', o, wildcard, 1, trial


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    indir = 'diffusion_input'
    outdir = 'diffusion'
    prefix = outdir + '/design'
    wildcard = f'{prefix}*.pdb'

    config = configparser.ConfigParser()
    config.read('settings.conf')
    exe = f"python {config['Paths']['RFdiffusion']}/scripts/run_inference.py"
    cache = Path(expandvars(config['Paths']['cache']))

    st.title('Motif Scaffolding')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    if active is not None:
        active = Path(active)
        with tab2:
            results = sorted(active.parent.glob(wildcard))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    cfg = get_config(active)
    config = cfg['diffusion']
    with tab1:
        with st.form('form'):
            st.file_uploader('Input a PDB for motif reference', '.pdb', key='protein')
            st.write('**Saved Motif Provider:**', config['protein'])
            col1, col2 = st.columns(2)
            col1.number_input('Number of designs', 1, value=config['n_design'], step=10, format='%d', key='n_design')
            col1.checkbox('Use beta model', config['beta'], key='beta')
            col2.number_input('Number of timestamps', 15, value=config['n_timestamp'], step=10, format='%d', key='n_timestamp')
            pdb = None
            if active is not None and config['protein'] is not None:
                pdb = active.parent / indir / config['protein']
            st.subheader('Contigs Setting')
            table_edit(config['contig'], pdb, key='contig')
            st.write('*Save your protein file to refresh the chain choices.*')
            st.subheader('Inpaint Setting')
            table_edit(config['inpaint'], pdb, key='inpaint')
            st.write('*Save your protein file to refresh the chain choices.*')
            col1, col2, col3 = st.columns(3)
            clicked1 = col1.form_submit_button('TEST', use_container_width=True)
            col2.form_submit_button('SAVE', use_container_width=True, on_click=save, disabled=active is None)
            clicked2 = col3.form_submit_button('PROCESS', use_container_width=True, type='primary', on_click=save, disabled=active is None)

    if process_ongoing() and (clicked1 or clicked2):
        st.toast('Process busy!', icon="🚨")
    elif clicked1:
        try_run()
    elif clicked2:
        setup_process(active)

    if process_ongoing():
        progress()
