const fs = require('fs');
const path = 'index.html';
let html = fs.readFileSync(path, 'utf8');

const logoPath = '/assets/clearglass-logo.png';
const logoUrl = 'https://www.clearglassinc.com/assets/clearglass-logo.png';

html = html.replace(/https:\/\/clearglassinc\.github\.io\/logo\.png/g, logoUrl);
html = html.replace(/https:\/\/clearglassinc\.github\.io\/(?:logo\.png|clear-glass-logo\.png|ClearGlassLogo\.png|0A141920-C68E-4DFD-9E7A-449AEC7D16D7\.jpeg|EBBD4D0A-D16F-418D-BC5E-45D13786A705\.jpeg|105D406B-3960-4B07-BF0C-82ED7425B658\.jpeg|a_clean_mobile_website_app_ui_screenshot_smartpho\.png)/g, logoUrl);
html = html.replace(/src="(?:logo\.png|clear-glass-logo\.png|ClearGlassLogo\.png|0A141920-C68E-4DFD-9E7A-449AEC7D16D7\.jpeg|EBBD4D0A-D16F-418D-BC5E-45D13786A705\.jpeg|105D406B-3960-4B07-BF0C-82ED7425B658\.jpeg|a_clean_mobile_website_app_ui_screenshot_smartpho\.png)"/g, `src="${logoPath}"`);

html = html.replace(
  /<div class="nav-mark"><img src="[^"]+" alt="ClearGlass logo"><\/div>/,
  `<div class="nav-mark"><img src="${logoPath}" alt="ClearGlass Inc. logo"></div>`
);

html = html.replace(
  /<div class="footer-mark"><img src="[^"]+" alt="ClearGlass logo"><\/div>/,
  `<div class="footer-mark"><img src="${logoPath}" alt="ClearGlass Inc. logo"></div>`
);

const css = `.artemis-core{margin-top:54px;text-align:center;display:flex;flex-direction:column;align-items:center;pointer-events:none;animation:fadeUp 1s ease .52s both}.artemis-emblem{width:62px;height:62px;border-radius:50%;border:2px solid rgba(20,20,24,.24);display:flex;align-items:center;justify-content:center;font-size:34px;color:#111116;background:rgba(255,255,255,.58);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);animation:artemisFloat 4.8s ease-in-out infinite,artemisPulse 3.2s ease-in-out infinite}.artemis-title{margin-top:22px;font-family:var(--serif);font-size:48px;line-height:1;color:#060609;letter-spacing:-.04em}.artemis-title span{font-size:26px;color:#f0a9b4;letter-spacing:.04em}.artemis-subtitle{margin-top:16px;font-family:var(--mono);font-size:18px;letter-spacing:.18em;color:#a2a5b1}@keyframes artemisFloat{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-9px) rotate(3deg)}}@keyframes artemisPulse{0%,100%{box-shadow:0 0 0 rgba(170,170,190,0)}50%{box-shadow:0 0 34px rgba(170,170,190,.34)}}`;
if (!html.includes('.artemis-core{')) {
  html = html.replace('</style>', `${css}\n</style>`);
}

const artemisBlock = `<section class="artemis-core" aria-label="Artemis VI flagship core"><div class="artemis-emblem" aria-hidden="true">✦</div><div class="artemis-title">Artemis <span>VI</span></div><div class="artemis-subtitle">FLAGSHIP CORE</div></section>`;
html = html.replace(
  /<div class="hero-actions"><a href="#products" class="btn btn-dark">Explore Platforms →<\/a><a href="artemis-iv\.html" class="btn btn-glass">Open Artemis IV Core<\/a><\/div>/,
  `<div class="hero-actions"><a href="#products" class="btn btn-dark">Explore Platforms →</a></div>${artemisBlock}`
);

fs.writeFileSync(path, html);
console.log('ClearGlass homepage patch applied. Verify index.html then commit.');
