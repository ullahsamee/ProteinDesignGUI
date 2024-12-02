import sys
from pathlib import Path
from Bio import SeqIO


if __name__ == '__main__':
    indir = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    for fa in indir.glob('*.fasta'):
        for rank, record in enumerate(SeqIO.parse(fa, 'fasta')):
            metadata = record.description.split(", ")
            metadata_dict = {item.split("=")[0]: item.split("=")[1] for item in metadata if "=" in item}
            if 'sample' not in metadata_dict:
                metadata_dict['sample'] = 1
            name = fa.stem
            if name.startswith('design_'):
                name = f'Design{name[7:]}'
            with open(outdir / f'{name}_Sample{metadata_dict["sample"]}_Rank{rank + 1}.fasta', 'w') as f:
                for i, ch in enumerate(str(record.seq).split(':')):
                    f.write(f'>{chr(i + 65)}|protein\n')
                    f.write(ch + '\n')


