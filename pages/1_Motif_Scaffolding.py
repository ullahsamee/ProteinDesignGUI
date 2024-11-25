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
    config['contig'] = table_update(config['contig'], state['contig'])
    config['inpaint'] = table_update(config['inpaint'], state['inpaint'])


def save():
    sync()
    c = get_config(active_trial)
    c['diffusion'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def batch():
    if process_ongoing() and not batch_ongoing():
        st.toast('Process busy!', icon="🚨")
    else:
        state['automated'] = False
        for i, path in enumerate(trials):
            try:
                if not process_ongoing() and (state['batch_progress'] < i or not batch_ongoing()):
                    wkdir = path.parent
                    shutil.rmtree(wkdir / outdir, ignore_errors=True)
                    cfg = get_config(path)
                    cmd = get_cmd(wkdir, **cfg['diffusion'])
                    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                    state['process_args'] = cfg['diffusion']['n_design'], f'Running inference for {cfg["name"]} ({i}/{len(trials)})', wkdir, wildcard
                    state['batch_progress'] = i
                if i == state['batch_progress']:
                    progress(side_placeholder)
            except Exception as e:
                st.write(e)
            finally:
                reset_proc()
        signify_batch_complete(side_placeholder)
        state['batch_progress'] = np.inf

        if state['proceed1']:
            state['automated'] = True
            st.switch_page('pages/2_ProteinMPNN.py')


if __name__ == '__main__':
    st.set_page_config('Protein Design: Motif Scaffolding')
    init()

    trials = state['trials']
    outdir = 'diffusion'
    prefix = outdir + '/design'
    wildcard = f'{prefix}*.pdb'
    if state['current_page'] != 1:
        abort_proc()
    state['current_page'] = 1

    side_placeholder, batch_clicked = navigation()
    post_batch = False

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"python {config['PATH']['RFdiffusion']}/scripts/run_inference.py"
    st.title('Motif Scaffolding')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    with tab1:
        ops = 0
        if trials and state['current_trial'] is not None:
            ops = trials.index(state['current_trial'])
        active_trial = state['current_trial'] = st.selectbox("Select a trial", trials, ops)
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
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1 and batch_ongoing() or batch_clicked:
                batch()
                post_batch = True
            elif clicked2:
                sync()
                if batch_ongoing():
                    st.toast('Process busy!', icon="🚨")
                    batch()
                    post_batch = True
                else:
                    try:
                        if not process_ongoing():
                            wkdir = active_trial.parent
                            shutil.rmtree(wkdir / outdir, ignore_errors=True)
                            cmd = get_cmd(wkdir, **config)
                            state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                            state['process_args'] = state['n_design'], 'Running inference for single trial..', wkdir, wildcard
                        else:
                            st.toast('Process busy!', icon="🚨")
                        progress(st)
                        signify_complete(st)
                    except Exception as e:
                        st.write(e)
                    finally:
                        reset_proc()

    with tab2:
        if active_trial is not None:
            results = sorted(active_trial.parent.glob(wildcard))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    if post_batch:
        if state['proceed1']:
            state['automated'] = True
            st.switch_page('pages/2_ProteinMPNN.py')