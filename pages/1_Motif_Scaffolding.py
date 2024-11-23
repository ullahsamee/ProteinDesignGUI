from common import *

state = st.session_state


def get_cmd(wkdir, protein, contig, inpaint, n_design, n_timestamp):
    cmd = f"""
    cd {wkdir}
    {exe} inference.output_prefix={prefix} inference.input_pdb={protein} \
    'contigmap.contigs={convert_selection(contig)}' inference.num_designs={n_design} diffuser.T={n_timestamp}"""
    temp = convert_selection(inpaint)
    if len(temp) > 2:
        cmd += f" 'contigmap.inpaint_seq={temp}'"
    return cmd


def sync():
    config['n_design'] = state['n_design']
    config['n_timestamp'] = state['n_timestamp']
    config['contig'] = state['contig'].to_dict('list')
    config['inpaint'] = state['inpaint'].to_dict('list')


def save():
    sync()
    c = get_config(active_trial)
    c['diffusion'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def run():
    sync()
    if state['batch_progress'] >= 0 or state['progress_type'] not in 'diffusion':
        st.toast('Process busy!', icon="🚨")
    else:
        try:
            state['progress_type'] = 'diffusion'
            if state['process'] is None:
                wkdir = active_trial.parent
                shutil.rmtree(wkdir / outdir, ignore_errors=True)
                cmd = get_cmd(wkdir, **config)
                state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                state['process_args'] = state['n_design'], 'Running inference for single trial..', wkdir, prefix
            else:
                st.toast('Process busy!', icon="🚨")
            progress(placeholder)
            signify_complete(placeholder)
        except Exception as e:
            state['process'].terminate()
            st.write(e)
        finally:
            state['progress_type'] = ''
            state['process'] = None


def batch():
    if process_ongoing() and state['batch_progress'] < 0 or state['progress_type'] not in 'diffusion':
        st.toast('Process busy!', icon="🚨")
    else:
        state['progress_type'] = 'diffusion'
        for i, path in enumerate(trials):
            try:
                if not process_ongoing() and state['batch_progress'] < i:
                    wkdir = path.parent
                    shutil.rmtree(wkdir / outdir, ignore_errors=True)
                    cfg = get_config(path)
                    cmd = get_cmd(wkdir, **cfg['diffusion'])
                    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                    state['process_args'] = cfg['diffusion']['n_design'], f'Running inference for {cfg["name"]} ({i}/{len(trials)})', wkdir, prefix
                    state['batch_progress'] = i
                if i == state['batch_progress']:
                    progress(side_placeholder)
            except Exception as e:
                state['process'].terminate()
                st.write(e)
            finally:
                if not process_ongoing():
                    state['process'] = None
        signify_batch_complete(side_placeholder)
        state['progress_type'] = ''
        state['batch_progress'] = -1


if __name__ == '__main__':
    st.set_page_config('Protein Design: Motif Scaffolding')

    trials = state['trials']
    state['current_batch'] = batch
    outdir = 'diffusion'
    prefix = outdir + '/design'

    side_placeholder = init()

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"python {config['PATH']['RFdiffusion']}/scripts/run_inference.py"
    st.title('Motif Scaffolding')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['diffusion']
            with st.form('diffusion_form'):
                col1, col2 = st.columns(2)
                col1.number_input('Number of designs', 1, value=config['n_design'], step=10, format='%d', key='n_design')
                col2.number_input('Number of timestamps', 15, value=config['n_timestamp'], step=10, format='%d', key='n_timestamp')
                pdb = active_trial.parent / config['protein']
                st.subheader('Contigs Setting')
                table_edit(config['contig'], pdb, key='contig')
                st.subheader('Inpaint Setting')
                table_edit(config['inpaint'], pdb, key='inpaint')
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True, on_click=save)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary', on_click=run)
    with tab2:
        if active_trial is not None:
            results = sorted(active_trial.parent.glob(f'{prefix}*.pdb'))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')
    placeholder = st.empty()

