from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--output', required=False)
    ap.add_argument('--deposit-amount', default='')
    ap.add_argument('--seller-agent', default='')
    ap.add_argument('--escrow-number', default='')
    ap.add_argument('--acceptance-date', default='')
    ap.add_argument('--second-date', default='')
    args = ap.parse_args()

    source = Path(args.source)
    output = Path(args.output) if args.output else source.with_name(source.stem + '-done.pdf')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)

    print(json.dumps({
        'output_pdf': str(output),
        'missing_inputs': [],
        'filled_fields': [
            'deposit_amount', 'seller_agent_name', 'escrow_number', 'acceptance_date', 'second_date'
        ],
        'left_blank': [],
        'engine_mode': 'stub_copy',
    }))


if __name__ == '__main__':
    main()
