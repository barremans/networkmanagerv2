// generate_floorplan_docx.js
// Gegenereerd door Networkmap_Creator — floorplan_docx_renderer.py
// Gebruik: node generate_floorplan_docx.js <data.json> <output.docx>

const fs   = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, AlignmentType, PageOrientation, BorderStyle, WidthType,
  ShadingType, VerticalAlign, HeadingLevel, PageBreak,
} = require('docx');

// ---------------------------------------------------------------------------
// Inladen data
// ---------------------------------------------------------------------------
const dataPath   = process.argv[2];
const outputPath = process.argv[3];
if (!dataPath || !outputPath) {
  console.error('Gebruik: node generate_floorplan_docx.js <data.json> <output.docx>');
  process.exit(1);
}

const payload = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const { floorplan, site, mappings } = payload;
// mappings = [ { svg_pt, mapped_val, type, outlet, endpoint, device, port, trace_steps } ]

// ---------------------------------------------------------------------------
// Stijl-helpers
// ---------------------------------------------------------------------------
const ACCENT   = '1F5C99';   // donkerblauw
const GROEN    = '4CAF7D';   // wandpunt
const BLAUW    = '2196F3';   // eindapparaat
const ORANJE   = 'FF7043';   // poort
const GRIJS    = 'F4F4F4';
const GRIJSDK  = 'EEEEEE';
const ZWART    = '111111';
const SUBTXT   = '555555';

const border_none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const borders_none = { top: border_none, bottom: border_none, left: border_none, right: border_none };
const border_thin  = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders_thin = { top: border_thin, bottom: border_thin, left: border_thin, right: border_thin };
const cm = dxa => Math.round(dxa * 567);  // cm → DXA (1 cm = 567 DXA)

// A4 landscape: content width = 16838 - 2*1134 = 14570 DXA (1.5cm margins)
const PAGE_W   = 16838;
const PAGE_H   = 11906;
const MARGIN   = 1134;   // 2cm
const CONTENT  = PAGE_W - 2 * MARGIN;  // 14570

function txt(text, opts = {}) {
  return new TextRun({
    text: String(text ?? '—'),
    font: 'Arial',
    size: opts.size ?? 22,       // 11pt default
    bold: opts.bold ?? false,
    color: opts.color ?? ZWART,
    italics: opts.italic ?? false,
  });
}

function para(children, opts = {}) {
  return new Paragraph({
    alignment: opts.align ?? AlignmentType.LEFT,
    spacing: { before: opts.before ?? 0, after: opts.after ?? 60 },
    children: Array.isArray(children) ? children : [children],
  });
}

function emptyLine() {
  return para([txt('')], { after: 0, before: 0 });
}

// ---------------------------------------------------------------------------
// Tabel-helper: 2-koloms label/waarde rijen
// ---------------------------------------------------------------------------
function infoTable(rows, colW1 = 2800) {
  const colW2 = CONTENT - colW1;
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [colW1, colW2],
    borders: borders_none,
    rows: rows.map(([label, value], i) =>
      new TableRow({
        children: [
          new TableCell({
            width: { size: colW1, type: WidthType.DXA },
            borders: borders_none,
            shading: { fill: i % 2 === 0 ? GRIJS : 'FFFFFF', type: ShadingType.CLEAR },
            margins: { top: 60, bottom: 60, left: 120, right: 60 },
            verticalAlign: VerticalAlign.CENTER,
            children: [para([txt(label, { color: SUBTXT, size: 20 })], { after: 0 })],
          }),
          new TableCell({
            width: { size: colW2, type: WidthType.DXA },
            borders: borders_none,
            shading: { fill: i % 2 === 0 ? GRIJS : 'FFFFFF', type: ShadingType.CLEAR },
            margins: { top: 60, bottom: 60, left: 60, right: 120 },
            verticalAlign: VerticalAlign.CENTER,
            children: [para([txt(value || '—', { bold: true, size: 20 })], { after: 0 })],
          }),
        ],
      })
    ),
  });
}

// 4-koloms tabel voor 2 secties naast elkaar
function sideBySideTable(leftRows, rightRows, title1, title2) {
  const halfW = Math.floor(CONTENT / 2) - 60;
  const labelW = Math.floor(halfW * 0.35);
  const valW   = halfW - labelW;

  function sectionCell(title, rows, fill) {
    const children = [
      para([txt(title, { bold: true, size: 20, color: ACCENT })],
           { before: 0, after: 60 }),
    ];
    rows.forEach(([label, value], i) => {
      children.push(new Table({
        width: { size: halfW, type: WidthType.DXA },
        columnWidths: [labelW, valW],
        borders: borders_none,
        rows: [new TableRow({
          children: [
            new TableCell({
              width: { size: labelW, type: WidthType.DXA },
              borders: borders_none,
              shading: { fill: i % 2 === 0 ? GRIJSDK : 'FFFFFF', type: ShadingType.CLEAR },
              margins: { top: 40, bottom: 40, left: 80, right: 40 },
              children: [para([txt(label, { color: SUBTXT, size: 20 })], { after: 0 })],
            }),
            new TableCell({
              width: { size: valW, type: WidthType.DXA },
              borders: borders_none,
              shading: { fill: i % 2 === 0 ? GRIJSDK : 'FFFFFF', type: ShadingType.CLEAR },
              margins: { top: 40, bottom: 40, left: 40, right: 80 },
              children: [para([txt(value || '—', { bold: true, size: 20 })], { after: 0 })],
            }),
          ],
        })],
      }));
    });
    return new TableCell({
      width: { size: halfW + 60, type: WidthType.DXA },
      borders: borders_none,
      shading: { fill: 'FFFFFF', type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 80, right: 80 },
      children,
    });
  }

  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [halfW + 60, halfW + 60],
    borders: { ...borders_none, insideV: border_thin },
    rows: [new TableRow({
      children: [
        sectionCell(title1, leftRows, GRIJSDK),
        sectionCell(title2, rightRows, 'FFFFFF'),
      ],
    })],
  });
}

// ---------------------------------------------------------------------------
// Badge-balk: gekleurde header met SVG-label
// ---------------------------------------------------------------------------
const COLOR_BG = { [GROEN]: 'E8F5EE', [BLAUW]: 'E3F2FD', [ORANJE]: 'FBE9E7' };

function badgeRow(svgPt, typeLabel, objName, color) {
  const bgFill = COLOR_BG[color] || 'F4F4F4';
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [CONTENT],
    borders: borders_none,
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT, type: WidthType.DXA },
        borders: borders_none,
        shading: { fill: bgFill, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [para([
          txt(`${svgPt}   `, { bold: true, size: 28, color: ZWART }),
          txt(typeLabel,     { bold: true, size: 24, color: color }),
          txt(objName ? `   |   ${objName}` : '', { bold: true, size: 24, color: ZWART }),
        ], { after: 0 })],
      })],
    })],
  });
}

// ---------------------------------------------------------------------------
// Sectie-kop binnen kaartje
// ---------------------------------------------------------------------------
function sectionTitle(label, color) {
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [CONTENT],
    borders: borders_none,
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT, type: WidthType.DXA },
        borders: borders_none,
        shading: { fill: GRIJSDK, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [para([txt(label, { bold: true, size: 20, color: color ?? ACCENT })], { after: 0 })],
      })],
    })],
  });
}

// ---------------------------------------------------------------------------
// Trace-sectie
// ---------------------------------------------------------------------------
function traceSection(steps) {
  const children = [sectionTitle('Trace', ACCENT)];
  if (!steps || steps.length === 0) {
    children.push(para([txt('Geen trace beschikbaar', { color: SUBTXT, size: 20, italic: true })],
                       { after: 60 }));
  } else {
    steps.slice(0, 6).forEach(s => {
      const prefix = s.obj_type === 'port' ? '->'
                   : s.obj_type === 'endpoint' ? '>'
                   : '>>';
      children.push(para([
        txt(prefix, { color: SUBTXT, size: 20 }),
        txt(`  ${s.label}`, { size: 20, color: ZWART }),
      ], { after: 40, before: 0 }));
    });
    if (steps.length > 6) {
      children.push(para([txt(`... (+${steps.length - 6} stappen)`,
                              { color: SUBTXT, size: 18, italic: true })], { after: 60 }));
    }
  }
  return children;
}

// ---------------------------------------------------------------------------
// Kaartje-builder per type
// ---------------------------------------------------------------------------
function buildCardOutlet(m) {
  const wo = m.outlet  ?? {};
  const ep = m.endpoint ?? null;
  const color = GROEN;
  const items = [];

  items.push(badgeRow(m.svg_pt, 'Wandpunt', wo.name ?? '', color));
  items.push(emptyLine());

  // Wandpunt + Eindapparaat naast elkaar
  const wpRows = [
    ['Naam:',     wo.name],
    ['Locatie:',  m.outlet_location_label ?? wo.location_description],
    ['VLAN:',     wo.vlan],
    ['Notities:', wo.notes],
  ];
  const epRows = ep ? [
    ['Naam:',        ep.name],
    ['Type:',        ep.type],
    ['IP adres:',    ep.ip],
    ['MAC adres:',   ep.mac],
    ['S/N:',         ep.serial],
    ['Merk:',        ep.brand],
    ['Model:',       ep.model],
    ['Notities:',    ep.notes],
  ] : [['', 'Geen eindapparaat']];

  items.push(sideBySideTable(wpRows, epRows, 'Wandpunt', 'Eindapparaat'));
  items.push(emptyLine());
  items.push(...traceSection(m.trace_steps));
  return items;
}

function buildCardEp(m) {
  const ep = m.endpoint ?? {};
  const color = BLAUW;
  const items = [];

  items.push(badgeRow(m.svg_pt, 'Eindapparaat', ep.name ?? '', color));
  items.push(emptyLine());
  items.push(sectionTitle('Eindapparaat', ACCENT));

  const leftRows = [
    ['Naam:',     ep.name],
    ['Type:',     ep.type],
    ['IP adres:', ep.ip],
    ['MAC adres:',ep.mac],
  ];
  const rightRows = [
    ['S/N:',      ep.serial],
    ['Merk:',     ep.brand],
    ['Model:',    ep.model],
    ['Locatie:',  ep.location],
    ['Notities:', ep.notes],
  ];
  items.push(sideBySideTable(leftRows, rightRows, 'Eindapparaat (links)', 'Details (rechts)'));
  items.push(emptyLine());
  items.push(...traceSection(m.trace_steps));
  return items;
}

function buildCardPort(m) {
  const dev  = m.device ?? {};
  const port = m.port   ?? {};
  const wo   = m.outlet ?? null;
  const color = ORANJE;
  const items = [];

  const objName = dev.name ?? '';
  items.push(badgeRow(m.svg_pt, 'Poort', objName, color));
  items.push(emptyLine());

  if (wo) {
    // 3 kolommen: Wandpunt | Device | Poort
    // Simuleer met 2 side-by-side tables gestapeld
    const woRows = [
      ['Naam:',     wo.name],
      ['Locatie:',  m.outlet_location_label ?? wo.location_description],
      ['VLAN:',     wo.vlan],
      ['Notities:', wo.notes],
    ];
    const devRows = [
      ['Naam:',  dev.name],
      ['Type:',  dev.type],
      ['IP:',    dev.ip],
      ['MAC:',   dev.mac],
      ['Rack:',  m.rack_location],
      ['Model:', dev.model],
    ];
    const portRows = [
      ['Naam:', port.name],
      ['Kant:', (port.side ?? '').toUpperCase()],
    ];
    items.push(sideBySideTable(woRows, devRows, 'Wandpunt', 'Device'));
    items.push(emptyLine());
    items.push(infoTable(portRows));
  } else {
    const devRows = [
      ['Naam:',  dev.name],
      ['Type:',  dev.type],
      ['IP:',    dev.ip],
      ['MAC:',   dev.mac],
      ['Rack:',  m.rack_location],
      ['Model:', dev.model],
    ];
    const portRows = [
      ['Naam:', port.name],
      ['Kant:', (port.side ?? '').toUpperCase()],
    ];
    items.push(sideBySideTable(devRows, portRows, 'Device', 'Poort'));
  }

  items.push(emptyLine());
  items.push(...traceSection(m.trace_steps));
  return items;
}

// ---------------------------------------------------------------------------
// Paginaheader
// ---------------------------------------------------------------------------
function makeHeader(floorplan, site, datum) {
  const fpName   = floorplan.name || floorplan.outlet_location_key || '';
  const siteName = site.name ?? '';
  return new Header({
    children: [
      new Table({
        width: { size: CONTENT, type: WidthType.DXA },
        columnWidths: [Math.floor(CONTENT * 0.7), Math.floor(CONTENT * 0.3)],
        borders: {
          ...borders_none,
          bottom: { style: BorderStyle.SINGLE, size: 4, color: ACCENT },
        },
        rows: [new TableRow({
          children: [
            new TableCell({
              width: { size: Math.floor(CONTENT * 0.7), type: WidthType.DXA },
              borders: borders_none,
              margins: { top: 60, bottom: 60, left: 0, right: 60 },
              children: [para([
                txt(fpName, { bold: true, size: 24, color: ZWART }),
                txt(siteName ? `   |   ${siteName}` : '', { size: 22, color: SUBTXT }),
              ], { after: 0 })],
            }),
            new TableCell({
              width: { size: Math.floor(CONTENT * 0.3), type: WidthType.DXA },
              borders: borders_none,
              margins: { top: 60, bottom: 60, left: 60, right: 0 },
              children: [para([txt(datum, { size: 20, color: SUBTXT })],
                              { after: 0, align: AlignmentType.RIGHT })],
            }),
          ],
        })],
      }),
    ],
  });
}

// ---------------------------------------------------------------------------
// Document opbouwen
// ---------------------------------------------------------------------------
const datum = new Date().toLocaleDateString('nl-BE', {
  day: '2-digit', month: '2-digit', year: 'numeric'
});

const header = makeHeader(floorplan, site, datum);

// Pagina 1: gekoppelde punten
const children = [
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [txt(`Gekoppelde punten  —  ${site.name ?? ''}`,
                   { bold: true, size: 28, color: ACCENT })],
    spacing: { before: 0, after: 200 },
  }),
];

mappings.forEach((m, i) => {
  let cardItems;
  if (m.type === 'ep')   cardItems = buildCardEp(m);
  else if (m.type === 'port') cardItems = buildCardPort(m);
  else                   cardItems = buildCardOutlet(m);

  children.push(...cardItems);

  // Paginawissel na elk kaartje behalve het laatste
  if (i < mappings.length - 1) {
    children.push(new Paragraph({
      children: [new PageBreak()],
      spacing: { before: 0, after: 0 },
    }));
  }
});

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: 'Arial', size: 22 } },
    },
    paragraphStyles: [
      {
        id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal',
        run: { size: 28, bold: true, font: 'Arial', color: ACCENT },
        paragraph: { spacing: { before: 0, after: 200 }, outlineLevel: 0 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: { default: header },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outputPath, buf);
  console.log('OK:' + outputPath);
}).catch(err => {
  console.error('ERROR:' + err.message);
  process.exit(1);
});