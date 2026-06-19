<script>
  let rpm = 3000;

  let bearingParams = {
    rollerCount: 10,
    pitchDiameter: 80,
    rollerDiameter: 12,
    contactAngle: 0
  };

  let gearParams = {
    pinionTeeth: 24,
    gearTeeth: 48
  };

  let showBearing = true;
  let showGear = true;

  let bearingFrequencies = null;
  let gearFrequencies = null;

  const bearingPresets = [
    { name: '深沟球轴承6205', rollerCount: 9, pitchDiameter: 38.5, rollerDiameter: 7.94, contactAngle: 0 },
    { name: '深沟球轴承6305', rollerCount: 10, pitchDiameter: 48, rollerDiameter: 11.11, contactAngle: 0 },
    { name: '圆柱滚子轴承NU205', rollerCount: 12, pitchDiameter: 44, rollerDiameter: 8, contactAngle: 0 }
  ];

  function rpmToHz(rpm) {
    return rpm / 60;
  }

  function hzToRpm(hz) {
    return hz * 60;
  }

  function degToRad(deg) {
    return deg * Math.PI / 180;
  }

  function calculateBearingFrequencies() {
    const N = bearingParams.rollerCount;
    const D = bearingParams.pitchDiameter;
    const d = bearingParams.rollerDiameter;
    const alpha = degToRad(bearingParams.contactAngle);
    const fr = rpmToHz(rpm);

    const ratio = d / D;
    const cosAlpha = Math.cos(alpha);

    const bpfo = (N / 2) * fr * (1 - ratio * cosAlpha);
    const bpfi = (N / 2) * fr * (1 + ratio * cosAlpha);
    const bsf = (D / (2 * d)) * fr * (1 - Math.pow(ratio, 2) * Math.pow(cosAlpha, 2));
    const ftf = 0.5 * fr * (1 - ratio * cosAlpha);

    bearingFrequencies = {
      BPFO: { hz: bpfo, rpm: hzToRpm(bpfo) },
      BPFI: { hz: bpfi, rpm: hzToRpm(bpfi) },
      BSF: { hz: bsf, rpm: hzToRpm(bsf) },
      FTF: { hz: ftf, rpm: hzToRpm(ftf) },
      rotational: { hz: fr, rpm: rpm }
    };
  }

  function calculateGearFrequencies() {
    const Z1 = gearParams.pinionTeeth;
    const Z2 = gearParams.gearTeeth;
    const fr = rpmToHz(rpm);

    const gmf = Z1 * fr;
    const gearRatio = Z1 / Z2;
    const gearRpm = rpm * gearRatio;
    const gearFr = rpmToHz(gearRpm);

    gearFrequencies = {
      pinion: {
        teeth: Z1,
        rpm: rpm,
        freq: fr
      },
      gear: {
        teeth: Z2,
        rpm: gearRpm,
        freq: gearFr
      },
      GMF: {
        hz: gmf,
        rpm: hzToRpm(gmf)
      },
      gearRatio: gearRatio
    };
  }

  function applyPreset(preset) {
    bearingParams.rollerCount = preset.rollerCount;
    bearingParams.pitchDiameter = preset.pitchDiameter;
    bearingParams.rollerDiameter = preset.rollerDiameter;
    bearingParams.contactAngle = preset.contactAngle;
    calculateAll();
  }

  function calculateAll() {
    if (showBearing) calculateBearingFrequencies();
    if (showGear) calculateGearFrequencies();
  }

  function formatValue(value, decimals = 2) {
    return value !== undefined && value !== null ? value.toFixed(decimals) : '-';
  }

  function validateBearingParams() {
    return bearingParams.rollerCount > 0 &&
           bearingParams.pitchDiameter > 0 &&
           bearingParams.rollerDiameter > 0 &&
           bearingParams.rollerDiameter < bearingParams.pitchDiameter;
  }

  function validateGearParams() {
    return gearParams.pinionTeeth > 0 && gearParams.gearTeeth > 0;
  }

  $: calculateAll();
</script>

<div class="calculator-page">
  <div class="header">
    <h1 class="page-title">特征频率计算器</h1>
    <p class="page-subtitle">计算轴承和齿轮的特征频率，用于故障诊断分析</p>
  </div>

  <div class="main-content">
    <div class="control-panel">
      <div class="panel-section">
        <h3 class="section-title">⚙️ 基础参数</h3>
        <div class="form-group">
          <label>转速 (RPM)</label>
          <input type="number" bind:value={rpm} min="100" max="20000" step="10" />
        </div>
        <div class="info-row">
          <span class="info-label">转频 (Hz)</span>
          <span class="info-value">{formatValue(rpmToHz(rpm))} Hz</span>
        </div>
      </div>

      <div class="panel-section">
        <div class="section-header">
          <h3 class="section-title">🔩 轴承参数</h3>
          <label class="toggle-switch">
            <input type="checkbox" bind:checked={showBearing} />
            <span class="toggle-slider"></span>
          </label>
        </div>

        {#if showBearing}
          <div class="preset-section">
            <label>轴承预设</label>
            <div class="preset-buttons">
              {#each bearingPresets as preset}
                <button class="preset-btn" on:click={() => applyPreset(preset)}>
                  {preset.name}
                </button>
              {/each}
            </div>
          </div>

          <div class="params-grid">
            <div class="form-group">
              <label>滚动体数量</label>
              <input type="number" bind:value={bearingParams.rollerCount} min="1" step="1" />
            </div>
            <div class="form-group">
              <label>节圆直径 (mm)</label>
              <input type="number" bind:value={bearingParams.pitchDiameter} min="0.1" step="0.1" />
            </div>
            <div class="form-group">
              <label>滚动体直径 (mm)</label>
              <input type="number" bind:value={bearingParams.rollerDiameter} min="0.1" step="0.1" />
            </div>
            <div class="form-group">
              <label>接触角 (°)</label>
              <input type="number" bind:value={bearingParams.contactAngle} min="0" max="45" step="1" />
            </div>
          </div>

          {#if !validateBearingParams()}
            <div class="error-message">
              ⚠️ 参数无效：滚动体直径必须小于节圆直径，且所有参数必须大于0
            </div>
          {/if}
        {/if}
      </div>

      <div class="panel-section">
        <div class="section-header">
          <h3 class="section-title">⚙️ 齿轮参数</h3>
          <label class="toggle-switch">
            <input type="checkbox" bind:checked={showGear} />
            <span class="toggle-slider"></span>
          </label>
        </div>

        {#if showGear}
          <div class="params-grid">
            <div class="form-group">
              <label>小齿轮齿数</label>
              <input type="number" bind:value={gearParams.pinionTeeth} min="1" step="1" />
            </div>
            <div class="form-group">
              <label>大齿轮齿数</label>
              <input type="number" bind:value={gearParams.gearTeeth} min="1" step="1" />
            </div>
          </div>

          {#if !validateGearParams()}
            <div class="error-message">
              ⚠️ 参数无效：齿数必须大于0
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <div class="display-panel">
      {#if showBearing && bearingFrequencies && validateBearingParams()}
        <div class="result-card">
          <div class="card-header">
            <h3 class="card-title">🔩 轴承特征频率</h3>
          </div>
          <div class="freq-grid">
            <div class="freq-item bpfo">
              <div class="freq-header">
                <span class="freq-name">BPFO</span>
                <span class="freq-desc">外圈故障频率</span>
              </div>
              <div class="freq-values">
                <span class="freq-hz">{formatValue(bearingFrequencies.BPFO.hz)} Hz</span>
                <span class="freq-rpm">{formatValue(bearingFrequencies.BPFO.rpm)} RPM</span>
              </div>
              <div class="freq-formula">
                (N/2) × f<sub>r</sub> × (1 - d/D × cosα)
              </div>
            </div>

            <div class="freq-item bpfi">
              <div class="freq-header">
                <span class="freq-name">BPFI</span>
                <span class="freq-desc">内圈故障频率</span>
              </div>
              <div class="freq-values">
                <span class="freq-hz">{formatValue(bearingFrequencies.BPFI.hz)} Hz</span>
                <span class="freq-rpm">{formatValue(bearingFrequencies.BPFI.rpm)} RPM</span>
              </div>
              <div class="freq-formula">
                (N/2) × f<sub>r</sub> × (1 + d/D × cosα)
              </div>
            </div>

            <div class="freq-item bsf">
              <div class="freq-header">
                <span class="freq-name">BSF</span>
                <span class="freq-desc">滚动体自转频率</span>
              </div>
              <div class="freq-values">
                <span class="freq-hz">{formatValue(bearingFrequencies.BSF.hz)} Hz</span>
                <span class="freq-rpm">{formatValue(bearingFrequencies.BSF.rpm)} RPM</span>
              </div>
              <div class="freq-formula">
                (D/2d) × f<sub>r</sub> × (1 - (d/D × cosα)²)
              </div>
            </div>

            <div class="freq-item ftf">
              <div class="freq-header">
                <span class="freq-name">FTF</span>
                <span class="freq-desc">保持架转速频率</span>
              </div>
              <div class="freq-values">
                <span class="freq-hz">{formatValue(bearingFrequencies.FTF.hz)} Hz</span>
                <span class="freq-rpm">{formatValue(bearingFrequencies.FTF.rpm)} RPM</span>
              </div>
              <div class="freq-formula">
                0.5 × f<sub>r</sub> × (1 - d/D × cosα)
              </div>
            </div>
          </div>

          <div class="harmonics-section">
            <h4 class="section-subtitle">谐波分析</h4>
            <div class="harmonics-table">
              <table>
                <thead>
                  <tr>
                    <th>谐波</th>
                    <th>BPFO (Hz)</th>
                    <th>BPFI (Hz)</th>
                    <th>BSF (Hz)</th>
                    <th>FTF (Hz)</th>
                  </tr>
                </thead>
                <tbody>
                  {#each [1, 2, 3, 4, 5] as n}
                    <tr>
                      <td>{n}x</td>
                      <td>{formatValue(bearingFrequencies.BPFO.hz * n)}</td>
                      <td>{formatValue(bearingFrequencies.BPFI.hz * n)}</td>
                      <td>{formatValue(bearingFrequencies.BSF.hz * n)}</td>
                      <td>{formatValue(bearingFrequencies.FTF.hz * n)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      {/if}

      {#if showGear && gearFrequencies && validateGearParams()}
        <div class="result-card">
          <div class="card-header">
            <h3 class="card-title">⚙️ 齿轮啮合频率</h3>
          </div>

          <div class="gear-info">
            <div class="gear-item">
              <span class="gear-label">小齿轮</span>
              <span class="gear-value">Z₁ = {gearFrequencies.pinion.teeth}, {formatValue(gearFrequencies.pinion.rpm)} RPM</span>
            </div>
            <div class="gear-item">
              <span class="gear-label">大齿轮</span>
              <span class="gear-value">Z₂ = {gearFrequencies.gear.teeth}, {formatValue(gearFrequencies.gear.rpm)} RPM</span>
            </div>
            <div class="gear-item">
              <span class="gear-label">传动比</span>
              <span class="gear-value">{formatValue(gearFrequencies.gearRatio, 4)}</span>
            </div>
          </div>

          <div class="gmf-display">
            <div class="gmf-main">
              <span class="gmf-label">啮合频率 GMF</span>
              <span class="gmf-value">{formatValue(gearFrequencies.GMF.hz)} Hz</span>
              <span class="gmf-rpm">{formatValue(gearFrequencies.GMF.rpm)} RPM</span>
            </div>
            <div class="gmf-formula">
              GMF = Z₁ × f<sub>r1</sub> = Z₂ × f<sub>r2</sub>
            </div>
          </div>

          <div class="sidebands-section">
            <h4 class="section-subtitle">边频带分析 (±n × f<sub>r</sub>)</h4>
            <div class="sidebands-grid">
              {#each [1, 2, 3] as n}
                <div class="sideband-item">
                  <span class="sideband-order">{n}x 边频带</span>
                  <div class="sideband-values">
                    <span>{formatValue(gearFrequencies.GMF.hz - n * gearFrequencies.pinion.freq)} Hz</span>
                    <span>←</span>
                    <span class="center-freq">{formatValue(gearFrequencies.GMF.hz)} Hz</span>
                    <span>→</span>
                    <span>{formatValue(gearFrequencies.GMF.hz + n * gearFrequencies.pinion.freq)} Hz</span>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      {#if !showBearing && !showGear}
        <div class="placeholder">
          <div class="placeholder-icon">🔬</div>
          <h3>请选择计算类型</h3>
          <p>开启轴承或齿轮参数以计算特征频率</p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .calculator-page {
    padding: 24px;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  }

  .header {
    margin-bottom: 24px;
  }

  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .page-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .main-content {
    display: grid;
    grid-template-columns: 400px 1fr;
    gap: 20px;
  }

  .control-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .panel-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 16px 0;
  }

  .section-header .section-title {
    margin: 0;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-group label {
    font-size: 13px;
    color: #374151;
    font-weight: 500;
  }

  .form-group input {
    padding: 10px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .form-group input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .params-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    margin-top: 12px;
  }

  .info-label {
    font-size: 13px;
    color: #6b7280;
  }

  .info-value {
    font-size: 16px;
    font-weight: 600;
    color: #3b82f6;
  }

  .preset-section {
    margin-bottom: 16px;
  }

  .preset-section label {
    font-size: 13px;
    color: #374151;
    font-weight: 500;
    display: block;
    margin-bottom: 8px;
  }

  .preset-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .preset-btn {
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .preset-btn:hover {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #3b82f6;
  }

  .error-message {
    padding: 10px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    color: #dc2626;
    font-size: 13px;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 48px;
    height: 24px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #d1d5db;
    transition: 0.3s;
    border-radius: 24px;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  input:checked + .toggle-slider {
    background-color: #3b82f6;
  }

  input:checked + .toggle-slider:before {
    transform: translateX(24px);
  }

  .display-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .result-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .card-header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid #f3f4f6;
  }

  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .freq-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .freq-item {
    padding: 16px;
    border-radius: 10px;
    border-left: 4px solid;
    background: #f9fafb;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .freq-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  }

  .freq-item.bpfo {
    border-left-color: #ef4444;
    background: linear-gradient(135deg, #fef2f2 0%, #fef9f9 100%);
  }

  .freq-item.bpfi {
    border-left-color: #f59e0b;
    background: linear-gradient(135deg, #fffbeb 0%, #fefefe 100%);
  }

  .freq-item.bsf {
    border-left-color: #8b5cf6;
    background: linear-gradient(135deg, #faf5ff 0%, #fefefe 100%);
  }

  .freq-item.ftf {
    border-left-color: #10b981;
    background: linear-gradient(135deg, #ecfdf5 0%, #fefefe 100%);
  }

  .freq-header {
    margin-bottom: 12px;
  }

  .freq-name {
    display: block;
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 4px;
  }

  .freq-desc {
    font-size: 12px;
    color: #6b7280;
  }

  .freq-values {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
  }

  .freq-hz {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
  }

  .freq-rpm {
    font-size: 14px;
    color: #6b7280;
  }

  .freq-formula {
    font-size: 11px;
    color: #9ca3af;
    font-family: 'Courier New', monospace;
    padding: 6px 8px;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 4px;
  }

  .section-subtitle {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    margin: 0 0 12px 0;
  }

  .harmonics-section {
    padding-top: 20px;
    border-top: 1px solid #f3f4f6;
  }

  .harmonics-table {
    overflow-x: auto;
  }

  .harmonics-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .harmonics-table th {
    background: #f9fafb;
    padding: 10px 12px;
    text-align: center;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #e5e7eb;
  }

  .harmonics-table td {
    padding: 8px 12px;
    text-align: center;
    border-bottom: 1px solid #f3f4f6;
    color: #6b7280;
  }

  .harmonics-table tr:hover td {
    background: #f9fafb;
  }

  .gear-info {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }

  .gear-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #f9fafb;
    border-radius: 8px;
  }

  .gear-label {
    font-size: 13px;
    color: #6b7280;
  }

  .gear-value {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .gmf-display {
    text-align: center;
    padding: 24px;
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-radius: 12px;
    margin-bottom: 20px;
  }

  .gmf-label {
    display: block;
    font-size: 14px;
    color: #3b82f6;
    font-weight: 500;
    margin-bottom: 8px;
  }

  .gmf-value {
    display: block;
    font-size: 42px;
    font-weight: 800;
    color: #1e40af;
    margin-bottom: 4px;
  }

  .gmf-rpm {
    display: block;
    font-size: 16px;
    color: #3b82f6;
    margin-bottom: 12px;
  }

  .gmf-formula {
    font-size: 12px;
    color: #60a5fa;
    font-family: 'Courier New', monospace;
  }

  .sidebands-section {
    padding-top: 20px;
    border-top: 1px solid #f3f4f6;
  }

  .sidebands-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sideband-item {
    padding: 12px 16px;
    background: #f9fafb;
    border-radius: 8px;
  }

  .sideband-order {
    display: block;
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 8px;
    font-weight: 500;
  }

  .sideband-values {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
  }

  .sideband-values span {
    flex: 1;
    text-align: center;
    color: #6b7280;
  }

  .sideband-values .center-freq {
    font-weight: 700;
    color: #3b82f6;
    background: #eff6ff;
    padding: 4px 8px;
    border-radius: 4px;
  }

  .placeholder {
    background: white;
    border-radius: 12px;
    padding: 80px 40px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .placeholder-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .placeholder h3 {
    font-size: 20px;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .placeholder p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  @media (max-width: 1024px) {
    .main-content {
      grid-template-columns: 1fr;
    }
  }
</style>
