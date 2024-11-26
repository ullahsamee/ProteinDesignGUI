from common import *
import configparser


state = st.session_state


def get_cmd(wkdir, n_recycle, n_mod, use_amber, use_template):
    cmd = f"""
    # Function to handle signals
    cleanup() {{
        echo "Signal received. Killing subprocess..."
        if [ -n "$pid" ] && ps -p $pid > /dev/null; then
            kill $pid
        fi
        echo "Cleanup complete. Exiting."
        exit 0
    }}
    trap cleanup SIGINT SIGTERM
    cd {wkdir}
    ls seqs/*.fasta | while read fa; do
        trap cleanup SIGINT SIGTERM
        source {conda}
        conda activate {env}
        outdir={outdir}/`basename $fa .fasta`
        mkdir -p $outdir
        {exe} $fa $outdir --num-models {n_mod} --num-recycle {n_recycle} {'--amber' if use_amber else ''} {'--template' if use_template else ''} &
        pid=$!
        wait $pid
    done &
    pid=$!
    wait $pid
    """
    return cmd


def sync():
    config['use_amber'] = state['use_amber']
    config['use_template'] = state['use_template']
    config['n_mod'] = state['n_mod']
    config['n_recycle'] = state['n_recycle']


def save():
    sync()
    c = get_config(active_trial)
    c['fold'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def batch(target=None):
    if process_ongoing() and not batch_ongoing():
        st.toast('Process busy!', icon="🚨")
    else:
        state['automated'] = False
        for i, path in enumerate(trials):
            if path != target and i != target:
                continue
            try:
                if not process_ongoing() and (state['batch_progress'] < i or not batch_ongoing()):
                    wkdir = path.parent
                    shutil.rmtree(wkdir / outdir, ignore_errors=True)
                    cfg = get_config(path)['fold']
                    cmd = get_cmd(wkdir, **cfg)
                    nfiles = len([*wkdir.glob('seqs/*.fasta')])
                    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd], shell=True)
                    state['process_args'] = cfg['n_mod'] * nfiles, f'Running prediction.. ({0}/{len(trials)})', wkdir, wildcard
                    state['batch_progress'] = i
                if i == state['batch_progress']:
                    progress(side_placeholder)
            except Exception as e:
                st.write(e)
            finally:
                reset_proc()
        signify_batch_complete(side_placeholder)
        state['batch_progress'] = np.inf


if __name__ == '__main__':
    st.set_page_config('Protein Design: Local ColabFold')
    init()

    trials = state['trials']
    outdir = 'fold'
    wildcard = f'{outdir}/*'
    state['current_page'] = 3

    side_placeholder, batch_clicked, single_clicked = navigation()

    config = configparser.ConfigParser()
    config.read('settings.conf')
    conda = f"{config['PATH']['ColabFold']}/conda/etc/profile.d/conda.sh"
    env = f"{config['PATH']['ColabFold']}/colabfold-conda"
    exe = f"{config['PATH']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    st.title('Local ColabFold')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    with tab1:
        ops = 0
        if trials and state['current_trial'] is not None:
            ops = trials.index(state['current_trial'])
        active_trial = state['current_trial'] = st.selectbox("Select a trial", trials, ops)
        if active_trial is not None:
            config = get_config(active_trial)['fold']
            with st.form(key='fold'):
                st.checkbox('Use amber', config['use_amber'], key='use_amber')
                st.checkbox('Use template', config['use_template'], key='use_template')
                st.selectbox('Number of models', [1, 2, 3, 4, 5], config['n_mod'] - 1, key='n_mod')
                st.number_input('Number of recycle', 1, value=config['n_recycle'], key='n_recycle')
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True, on_click=save)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1 and batch_ongoing() or batch_clicked or state['automated'] or single_clicked:
                if single_clicked:
                    batch(active_trial)
                else:
                    batch()
            elif clicked2:
                sync()
                if batch_ongoing():
                    st.toast('Process busy!', icon="🚨")
                    batch()
                else:
                    try:
                        if not process_ongoing():
                            wkdir = active_trial.parent
                            shutil.rmtree(wkdir / outdir, ignore_errors=True)
                            cmd = get_cmd(wkdir, **config)
                            state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                            nfiles = len([*wkdir.glob('seqs/*.fasta')])
                            state['process_args'] = config['n_mod'] * nfiles, 'Running prediction for single trial..', wkdir, wildcard
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
            results = sorted(active_trial.parent.rglob(f'{wildcard}*/*.pdb'))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    conclude(side_placeholder)
