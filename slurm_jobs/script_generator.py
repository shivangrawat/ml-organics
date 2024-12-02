import os

def generate_slurm_script(slurm_params, model_params, branch_name=None):
    # Construct the SLURM script header
    script_content = f'''#!/bin/bash
#SBATCH --nodes={slurm_params['nodes']}
#SBATCH --time={slurm_params['time']}
#SBATCH --ntasks-per-node={slurm_params['ntasks_per_node']}
#SBATCH --cpus-per-task={slurm_params['cpus_per_task']}
#SBATCH --job-name={slurm_params['job_name']}
#SBATCH --mem={slurm_params['mem']}
#SBATCH --gres=gpu:{slurm_params['gpus']}
#SBATCH --mail-type=ALL
#SBATCH --mail-user={slurm_params['mail_user']}
#SBATCH --output={slurm_params['output_file']}
'''

    # If branch_name is provided, set BRANCH_NAME variable
    if branch_name:
        script_content += f'\nBRANCH_NAME={branch_name}\n'
    else:
        script_content += f'\nBRANCH_NAME=main\n'  # Default to 'main' if not specified

    script_content += f'''
singularity exec --nv --overlay {slurm_params['singularity_overlay']}:ro {slurm_params['singularity_image']} /bin/bash -c "
source /ext3/env.sh; conda activate {slurm_params['conda_env']}; \
cd {slurm_params['repo_dir']}; \
git fetch origin; \
git checkout $BRANCH_NAME; \
git pull; \
cd {slurm_params['script_subdir']}; \
python {slurm_params['script_name']}.py \
'''

    # Add model parameters dynamically
    for key, value in model_params.items():
        if isinstance(value, bool):
            if value:
                script_content += f'--{key} \\\n'
        else:
            script_content += f'--{key} {value} \\\n'

    # Remove the last backslash and newline character
    script_content = script_content.rstrip("\\\n")
    
    # Close the singularity command
    script_content += '"\n'  # Close the double quotes of the bash command

    return script_content

def save_script(script_content, filename):
    with open(filename, 'w') as file:
        file.write(script_content)

if __name__ == "__main__":
    # Define SLURM parameters
    slurm_params = {
        "nodes": 1,
        "time": "18:00:00",
        "ntasks_per_node": 1,
        "cpus_per_task": 8,
        "job_name": "sMNIST",
        "mem": "64GB",
        "gpus": 1,
        "mail_user": "sr6364@nyu.edu",
        "output_file": "job.%j.out",
        "singularity_overlay": "/scratch/sr6364/overlay-files/overlay-50G-10M.ext3",
        "singularity_image": "/scratch/work/public/singularity/cuda11.8.86-cudnn8.7-devel-ubuntu22.04.2.sif",
        "conda_env": "feed-r-conda",
        "repo_dir": "/home/sr6364/python_scripts/dynamic-divisive-norm",  # Repository directory
        "script_subdir": "training_scripts/sMNIST",  # Subdirectory containing the script
        "script_name": "train"
    }

    # Define model parameters
    HIDDEN_SIZE = 128
    PERMUTED = False
    CHECKPOINT = False
    dt_tau_max_y = 0.05
    dt_tau_max_a = 0.01
    dt_tau_max_b = 0.1
    LEARNING_RATE = 0.01

    # List of branches to generate scripts for
    # branch_list = [
    #     "feature_diagonal_recurrence",
    #     "feature_a_clamped",
    #     "feature_recurrence_rectified",
    #     "feature_Wr_identity",
    #     "feature_Wr_identity_plus_ortho",
    #     "feature_weight_norm",
    #     "feature_recurrence_rectified_identity_perturbed",
    # ]
    branch_list = [
        "feature_diagonal_recurrence",
        "feature_recurrence_rectified",
        "feature_recurrence_rectified_identity_perturbed",
    ]
    # additional_name = "rectified_model_fixed_tau"
    additional_name = "rectified_model"

    for branch_name in branch_list:
        # Set append_name to branch_name, replacing slashes with underscores
        append_name = branch_name

        if PERMUTED:
            MODEL_NAME = f"psMNIST_{HIDDEN_SIZE}_{dt_tau_max_y}_{dt_tau_max_a}_{dt_tau_max_b}_lr_{LEARNING_RATE}_{additional_name}"
            FOLDER_NAME = f"/vast/sr6364/dynamic-divisive-norm/tb_logs/{append_name}/psMNIST"
        else:
            MODEL_NAME = f"sMNIST_{HIDDEN_SIZE}_{dt_tau_max_y}_{dt_tau_max_a}_{dt_tau_max_b}_lr_{LEARNING_RATE}_{additional_name}"
            FOLDER_NAME = f"/vast/sr6364/dynamic-divisive-norm/tb_logs/{append_name}/sMNIST"

        model_params = {
            "MODEL_NAME": MODEL_NAME,
            "FOLDER_NAME": FOLDER_NAME,
            "PERMUTED": PERMUTED,
            "CHECKPOINT": CHECKPOINT,
            "VERSION": 0,
            "SEQUENCE_LENGTH": 784,
            "dt_tau_max_y": dt_tau_max_y,
            "dt_tau_max_a": dt_tau_max_a,
            "dt_tau_max_b": dt_tau_max_b,
            "learn_tau": "True",
            "HIDDEN_SIZE": HIDDEN_SIZE,
            "NUM_EPOCHS": 300,
            "LEARNING_RATE": LEARNING_RATE,
            "SCHEDULER_CHANGE_STEP": 50,
            "SCHEDULER_GAMMA": 0.8
        }

        slurm_params["job_name"] = model_params["MODEL_NAME"]

        script_content = generate_slurm_script(slurm_params, model_params, branch_name=branch_name)
        if PERMUTED:
            # Replace slashes with underscores for directory names
            directory = f'psMNIST_{HIDDEN_SIZE}/{append_name}'
            if not os.path.exists(directory):
                os.makedirs(directory)
            # Use the MODEL_NAME as the script file name
            file_path = os.path.join(directory, f'{MODEL_NAME}.sh')
            save_script(script_content, file_path)
        else:
            directory = f'sMNIST_{HIDDEN_SIZE}/{append_name}'
            if not os.path.exists(directory):
                os.makedirs(directory)
            file_path = os.path.join(directory, f'{MODEL_NAME}.sh')
            save_script(script_content, file_path)
