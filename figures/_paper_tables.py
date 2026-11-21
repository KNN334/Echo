"""Shared rendering for the two manuscript tables; styles come from style/."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from style.palette import COLORS, LINEWIDTH, MM_PER_INCH, export_figure, figure_size
from _paper_common import Canvas, alignment, write_csv, write_json


def render_table(out, stem, title, headers, widths, rows, notes, *, height_mm,
                 row_height_mm, header_top_mm, auditor=None):
    """Render measured columns, section headings and footnotes at final size."""
    fig = plt.figure(figsize=figure_size(height_mm=height_mm))
    canvas = Canvas(fig)
    left, right = 6, 177
    assert abs(sum(widths) - (right-left)) < 1e-8
    starts = [left]
    for width in widths:
        starts.append(starts[-1]+width)
    texts = []

    def text(x, y, value, **kwargs):
        artist = canvas.text(x, y, value, va='baseline', **kwargs)
        texts.append(artist)
        return artist

    def rule(y, weight):
        fig.add_artist(Line2D([left/canvas.width, right/canvas.width],
                             [y/canvas.height, y/canvas.height], transform=fig.transFigure,
                             color=COLORS['axis'], linewidth=weight))

    text(left, height_mm-6, title, fontweight='bold')
    rule(header_top_mm, LINEWIDTH['primary'])
    cell_bounds = []
    for col, value in enumerate(headers):
        lines = value.split('\n')
        for line, label in enumerate(lines):
            x = starts[col]+1 if col == 0 else (starts[col]+starts[col+1])/2
            artist = text(x, header_top_mm-4-line*3.2, label,
                          ha='left' if col == 0 else 'center', fontweight='bold')
            cell_bounds.append((artist, starts[col]+.7, starts[col+1]-.7))
    header_bottom = header_top_mm-3.2*max(len(h.split('\n')) for h in headers)-2
    rule(header_bottom, LINEWIDTH['comparison'])
    y = header_bottom-4
    display_rows = []
    for section, cells in rows:
        assert len(cells) == len(headers)
        if section:
            artist = text(left+1, y, cells[0], fontweight='bold', color=COLORS['axis'])
            cell_bounds.append((artist, left+.7, right-.7))
        else:
            for col, value in enumerate(cells):
                x = starts[col]+1 if col == 0 else starts[col+1]-1
                artist = text(x, y, value, ha='left' if col == 0 else 'right')
                cell_bounds.append((artist, starts[col]+.7, starts[col+1]-.7))
        display_rows.append({'row_type':'section' if section else 'data',
                             **{h.replace('\n',' '):v for h,v in zip(headers,cells)}})
        y -= row_height_mm
    bottom = y+row_height_mm-1.7
    rule(bottom, LINEWIDTH['primary'])
    note_y = bottom-5
    for line in notes:
        text(left, note_y, line)
        note_y -= 3.8
    assert note_y > 0, 'Footnotes do not fit the final table size'

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for artist, x0, x1 in cell_bounds:
        box = artist.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
        bounds = [box.x0*MM_PER_INCH, box.y0*MM_PER_INCH,
                  box.x1*MM_PER_INCH, box.y1*MM_PER_INCH]
        assert bounds[0] >= x0 and bounds[2] <= x1, (artist.get_text(), bounds, x0, x1)
        boxes.append({'text':artist.get_text(),'bounds_mm':bounds,'column_limits_mm':[x0,x1]})
    for artist in texts:
        box = artist.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
        assert box.x0 >= 0 and box.y0 >= 0
        assert box.x1*MM_PER_INCH <= canvas.width and box.y1*MM_PER_INCH <= canvas.height
    table_ax = canvas.axes(left, bottom, right-left, header_top_mm-bottom)
    table_ax.set_axis_off()
    alignment(fig, out, stem, [table_ax], ['table'], [], [], auditor)
    write_json(out/(stem+'.cell_bounds.json'), {
        'width_mm':canvas.width,'height_mm':canvas.height,'columns_mm':starts,
        'minimum_font_pt':float(plt.rcParams['font.size']),
        'cell_fit_passed':True,'cells':boxes,'alignment_scope':'Single table; no comparable plot panels.'})
    export_figure(fig, out/stem)
    plt.close(fig)
    write_csv(out/'source_data/display_table.csv', display_rows)
    return {'width_mm':canvas.width,'height_mm':canvas.height,'bottom_rule_mm':bottom}


def write_markdown(path, caption, headers, rows, notes):
    clean = [h.replace('\n',' ') for h in headers]
    lines = [caption.strip(), '', '| '+' | '.join(clean)+' |',
             '| '+' | '.join(['---']*len(headers))+' |']
    for section, cells in rows:
        values = [f'**{value}**' if section and value else value for value in cells]
        lines.append('| '+' | '.join(values)+' |')
    lines.extend(['', *notes, ''])
    Path(path).write_text('\n'.join(lines),encoding='utf-8')
