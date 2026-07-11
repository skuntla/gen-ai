const DEFAULT_SKETCH = {
  stroke: "#111",
  strokeWidth: 2.5,
  roughness: 1.7,
  bowing: 1.2
};

function createGroup(svg, transform) {
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  if (transform) {
    group.setAttribute("transform", transform);
  }
  svg.appendChild(group);
  return group;
}

function drawSealedEnvelope(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 10
    })
  );
  parent.appendChild(rc.line(0, 0, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(w, 0, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(0, h, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(w, h, w / 2, h * 0.55, sketch));
  parent.appendChild(
    rc.circle(w * 0.78, h * 0.72, 10, {
      ...sketch,
      fill: "#f7d857",
      fillStyle: "solid"
    })
  );
}

function drawScriptPage(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 12
    })
  );
  parent.appendChild(rc.line(14, 18, w - 14, 18, sketch));
  parent.appendChild(rc.line(14, 30, w - 22, 30, sketch));
  parent.appendChild(rc.line(14, 42, w - 35, 42, sketch));
  parent.appendChild(
    rc.line(w * 0.72, 54, w * 0.72, 66, {
      ...sketch,
      strokeWidth: 3
    })
  );
  parent.appendChild(
    rc.line(w * 0.62, 60, w * 0.82, 60, {
      ...sketch,
      strokeWidth: 3
    })
  );
}

function drawResponseScroll(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 8, w, h - 16, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 11
    })
  );
  parent.appendChild(
    rc.path(`M 0 8 Q ${w / 2} 0 ${w} 8`, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
  parent.appendChild(
    rc.path(`M 0 ${h - 8} Q ${w / 2} ${h} ${w} ${h - 8}`, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
  parent.appendChild(rc.line(16, 28, w - 16, 28, sketch));
  parent.appendChild(rc.line(16, 40, w - 24, 40, sketch));
  parent.appendChild(rc.line(16, 52, w - 30, 52, sketch));
}

function drawServerCloud(rc, parent, sketch) {
  parent.appendChild(
    rc.ellipse(70, 18, 120, 42, {
      ...sketch,
      fill: "#f5f5f5",
      fillStyle: "hachure",
      hachureGap: 14
    })
  );
  parent.appendChild(
    rc.rectangle(28, 42, 84, 58, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 10
    })
  );
  parent.appendChild(rc.line(40, 58, 100, 58, sketch));
  parent.appendChild(rc.line(40, 72, 88, 72, sketch));
  parent.appendChild(rc.line(40, 86, 76, 86, sketch));
  parent.appendChild(
    rc.circle(16, 58, 8, {
      ...sketch,
      fill: "#222"
    })
  );
  parent.appendChild(
    rc.circle(124, 58, 8, {
      ...sketch,
      fill: "#222"
    })
  );
}

function drawEnvelope(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 10
    })
  );
  parent.appendChild(rc.line(0, 0, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(w, 0, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(0, h, w / 2, h * 0.55, sketch));
  parent.appendChild(rc.line(w, h, w / 2, h * 0.55, sketch));
}

function drawTruck(rc, parent, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, 80, 55, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure"
    })
  );
  parent.appendChild(
    rc.path("M80 20 L105 20 L115 55 L80 55 Z", {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure"
    })
  );
  parent.appendChild(
    rc.circle(24, 58, 18, {
      ...sketch,
      fill: "#222"
    })
  );
  parent.appendChild(
    rc.circle(94, 58, 18, {
      ...sketch,
      fill: "#222"
    })
  );
  parent.appendChild(rc.rectangle(88, 27, 15, 13, sketch));
}

function drawLetter(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 12
    })
  );
  parent.appendChild(rc.line(15, 18, w - 15, 18, sketch));
  parent.appendChild(rc.line(15, 30, w - 22, 30, sketch));
  parent.appendChild(rc.line(15, 42, w - 35, 42, sketch));
}

function drawVendingMachine(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#f5f5f5",
      fillStyle: "hachure",
      hachureGap: 12
    })
  );
  parent.appendChild(
    rc.rectangle(18, 18, w - 36, h * 0.42, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
  parent.appendChild(
    rc.rectangle(w * 0.62, h * 0.62, 22, 22, {
      ...sketch,
      fill: "#f7d857",
      fillStyle: "solid"
    })
  );
  parent.appendChild(rc.line(24, h * 0.72, w - 24, h * 0.72, sketch));
  parent.appendChild(
    rc.rectangle(34, h * 0.76, 28, 14, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure"
    })
  );
}

function drawReceipt(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.rectangle(0, 0, w, h, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "hachure",
      hachureGap: 10
    })
  );
  parent.appendChild(rc.line(12, 16, w - 12, 16, sketch));
  parent.appendChild(rc.line(12, 28, w - 18, 28, sketch));
  parent.appendChild(rc.line(12, 40, w - 14, 40, sketch));
  parent.appendChild(rc.line(12, 52, w - 20, 52, sketch));
  parent.appendChild(rc.line(12, 64, w - 16, 64, sketch));
  parent.appendChild(
    rc.path(`M 8 ${h - 8} L 16 ${h - 2} L 24 ${h - 8} L 32 ${h - 2} L 40 ${h - 8}`, sketch)
  );
}

function drawToteBag(rc, parent, { w, h }, sketch) {
  parent.appendChild(
    rc.path(`M 18 24 Q ${w / 2} 6 ${w - 18} 24`, sketch)
  );
  parent.appendChild(
    rc.path(
      `M 12 24 L 18 24 L 22 ${h - 10} Q ${w / 2} ${h + 4} ${w - 22} ${h - 10} L ${w - 18} 24 L ${w - 12} 24`,
      {
        ...sketch,
        fill: "#fff8ed",
        fillStyle: "hachure",
        hachureGap: 11
      }
    )
  );
  parent.appendChild(
    rc.rectangle(w * 0.22, 8, w * 0.18, 20, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
  parent.appendChild(
    rc.rectangle(w * 0.46, 2, w * 0.16, 24, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
  parent.appendChild(
    rc.rectangle(w * 0.66, 10, w * 0.18, 18, {
      ...sketch,
      fill: "#fff8ed",
      fillStyle: "solid"
    })
  );
}

const ILLUSTRATION_DRAWERS = {
  "sealed-envelope": drawSealedEnvelope,
  "script-page": drawScriptPage,
  "response-scroll": drawResponseScroll,
  "server-cloud": drawServerCloud,
  "vending-machine": drawVendingMachine,
  receipt: drawReceipt,
  "tote-bag": drawToteBag,
  envelope: drawEnvelope,
  truck: drawTruck,
  letter: drawLetter
};

function drawIllustration(rc, svg, item, sketch = DEFAULT_SKETCH) {
  const drawer = ILLUSTRATION_DRAWERS[item.type];
  if (!drawer) {
    return;
  }

  const w = item.w ?? 100;
  const h = item.h ?? 70;
  const rotation = item.rotation ?? 0;
  const scale = item.scale ?? 1;
  let transform = `translate(${item.x} ${item.y})`;

  if (item.type === "server-cloud") {
    transform += ` scale(${scale})`;
  } else if (item.type === "truck") {
    transform += ` scale(${scale})`;
  } else {
    transform += ` rotate(${rotation})`;
  }

  const group = createGroup(svg, transform);
  drawer(rc, group, { w, h }, sketch);
}

function drawPath(rc, svg, pathConfig, sketch = DEFAULT_SKETCH) {
  if (!pathConfig?.d) {
    return;
  }

  svg.appendChild(
    rc.path(pathConfig.d, {
      ...sketch,
      strokeWidth: pathConfig.strokeWidth ?? 2,
      strokeLineDash: pathConfig.strokeLineDash ?? [10, 10]
    })
  );
}

function renderIllustrations(rc, svg, scene, sketch = DEFAULT_SKETCH) {
  for (const item of scene.illustrations ?? []) {
    drawIllustration(rc, svg, item, sketch);
  }
}

if (typeof module !== "undefined") {
  module.exports = {
    DEFAULT_SKETCH,
    drawIllustration,
    drawPath,
    renderIllustrations
  };
}
