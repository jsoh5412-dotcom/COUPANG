// 고정 시드로 같은 그래픽을 재현한다
  let seed = 33;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  document.querySelectorAll('[data-powder]').forEach((el) => {
    const [x, y, w, h] = el.dataset.box.split(',').map(Number);
    for (let i = 0; i < Number(el.dataset.powder); i++) {
      const p = document.createElement('i');
      const s = 2 + rnd() * rnd() * 10;
      p.style.cssText = `left:${x + rnd() * w}px;top:${y + rnd() * h}px;width:${s}px;height:${s}px;opacity:${0.5 + rnd() * 0.5}`;
      el.appendChild(p);
    }
  });
  const check = '<svg width="50" height="50" viewBox="0 0 50 50"><circle cx="25" cy="25" r="25" fill="#0B6FD1"/><path d="M13 26l9 9 16-18" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  document.querySelectorAll('[data-check] li').forEach((li) => { li.innerHTML = check + '<span>' + li.innerHTML + '</span>'; });
