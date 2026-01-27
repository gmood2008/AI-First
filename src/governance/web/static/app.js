/**
 * Reference Web Governance Console - Client
 * 
 * 核心原则：
 * - 所有逻辑在 API 层
 * - UI 只是 API 的客户端
 * - UI 可删除，治理系统仍然完整
 * 
 * ⚠️ 禁止事项：
 * - ❌ UI 直接写 Registry
 * - ❌ UI 计算 Health / Risk
 * - ❌ UI 决定 Capability 状态
 * - ❌ UI 绕过 Proposal 流程
 */

// API 基础 URL（实际部署时需要配置）
const API_BASE = '/api/governance';

// 工具函数
const api = {
    async get(url) {
        const response = await fetch(`${API_BASE}${url}`);
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        return response.json();
    },
    
    async post(url, data) {
        const response = await fetch(`${API_BASE}${url}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        return response.json();
    }
};

// Tab 切换
document.querySelectorAll('.nav-tabs li').forEach(tab => {
    tab.addEventListener('click', () => {
        // 更新 active 状态
        document.querySelectorAll('.nav-tabs li').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
        
        // 加载对应数据
        loadTabData(tab.dataset.tab);
    });
});

// 加载 Tab 数据
async function loadTabData(tab) {
    try {
        if (tab === 'observatory') {
            await loadObservatory();
        } else if (tab === 'decision-room') {
            await loadDecisionRoom();
        } else if (tab === 'ecosystem') {
            await loadEcosystem();
        }
    } catch (error) {
        console.error('Failed to load tab data:', error);
        showError(error.message);
    }
}

// V1: Observatory
async function loadObservatory() {
    // 加载能力健康度
    const capabilities = await api.get('/capabilities');
    renderHealthMap(capabilities);
    
    // 加载风险分布
    const riskDist = await api.get('/capabilities/risk-distribution');
    renderRiskDistribution(riskDist);
    
    // 加载信号时间线（最近 50 条）
    const signals = await api.get('/signals?limit=50');
    renderSignalTimeline(signals);
    
    // 加载需求雷达
    const missing = await api.get('/demand/missing-capabilities?window_hours=24');
    renderDemandRadar(missing);
}

function renderHealthMap(capabilities) {
    const container = document.getElementById('health-map');
    
    if (capabilities.length === 0) {
        container.innerHTML = '<p>No capabilities found</p>';
        return;
    }
    
    const html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Capability ID</th>
                    <th>State</th>
                    <th>Health Score</th>
                    <th>Risk Level</th>
                </tr>
            </thead>
            <tbody>
                ${capabilities.map(cap => `
                    <tr>
                        <td>${cap.capability_id}</td>
                        <td><span class="badge badge-info">${cap.current_state}</span></td>
                        <td>${cap.health_score.toFixed(1)}%</td>
                        <td><span class="badge badge-${getRiskBadgeClass(cap.risk_level)}">${cap.risk_level}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function renderRiskDistribution(distribution) {
    const container = document.getElementById('risk-distribution');
    
    const html = `
        <div>
            <p><strong>Total Capabilities:</strong> ${distribution.total}</p>
            <div style="margin-top: 1rem;">
                ${Object.entries(distribution.distribution).map(([risk, count]) => `
                    <div style="margin-bottom: 0.5rem;">
                        <strong>${risk}:</strong> ${count} capabilities
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function renderSignalTimeline(signals) {
    const container = document.getElementById('signal-timeline');
    
    if (signals.length === 0) {
        container.innerHTML = '<p>No signals found</p>';
        return;
    }
    
    const html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Capability</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
                ${signals.slice(0, 20).map(signal => `
                    <tr>
                        <td>${new Date(signal.timestamp).toLocaleString()}</td>
                        <td>${signal.signal_type}</td>
                        <td>${signal.capability_id}</td>
                        <td><span class="badge badge-${getSeverityBadgeClass(signal.severity)}">${signal.severity}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function renderDemandRadar(missing) {
    const container = document.getElementById('demand-radar');
    
    if (missing.length === 0) {
        container.innerHTML = '<p>No missing capabilities detected</p>';
        return;
    }
    
    const html = `
        <table class="table">
            <thead>
                <tr>
                    <th>Capability ID</th>
                    <th>Frequency</th>
                    <th>First Seen</th>
                    <th>Last Seen</th>
                </tr>
            </thead>
            <tbody>
                ${missing.map(item => `
                    <tr>
                        <td>${item.capability_id}</td>
                        <td>${item.frequency}</td>
                        <td>${new Date(item.first_seen).toLocaleString()}</td>
                        <td>${new Date(item.last_seen).toLocaleString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

// V2: Decision Room
async function loadDecisionRoom() {
    const proposals = await api.get('/proposals?status=PENDING');
    renderProposalQueue(proposals);
}

function renderProposalQueue(proposals) {
    const container = document.getElementById('proposal-queue');
    
    if (proposals.length === 0) {
        container.innerHTML = '<p>No pending proposals</p>';
        return;
    }
    
    const html = proposals.map(proposal => `
        <div class="card proposal-card ${proposal.proposal_type.toLowerCase()}">
            <h3>${proposal.proposal_type}: ${proposal.target_capability_id}</h3>
            <p><strong>Created:</strong> ${new Date(proposal.created_at).toLocaleString()}</p>
            <p><strong>Created By:</strong> ${proposal.created_by}</p>
            <p><strong>Evidence:</strong> ${JSON.stringify(proposal.triggering_evidence, null, 2)}</p>
            <div style="margin-top: 1rem;">
                <button class="btn btn-primary" onclick="approveProposal('${proposal.proposal_id}')">Approve</button>
                <button class="btn btn-danger" onclick="rejectProposal('${proposal.proposal_id}')">Reject</button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

async function approveProposal(proposalId) {
    const rationale = prompt('Please provide rationale for approval:');
    if (!rationale) return;
    
    try {
        const decision = await api.post(`/proposals/${proposalId}/approve`, {
            decided_by: 'admin', // 实际应该从认证获取
            rationale: rationale
        });
        
        alert(`Proposal approved. Decision ID: ${decision.decision_id}`);
        loadDecisionRoom(); // 重新加载
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function rejectProposal(proposalId) {
    const rationale = prompt('Please provide rationale for rejection:');
    if (!rationale) return;
    
    try {
        const decision = await api.post(`/proposals/${proposalId}/reject`, {
            decided_by: 'admin', // 实际应该从认证获取
            rationale: rationale
        });
        
        alert(`Proposal rejected. Decision ID: ${decision.decision_id}`);
        loadDecisionRoom(); // 重新加载
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// V3: Ecosystem Ops
async function loadEcosystem() {
    // 加载采用指标
    const capabilities = await api.get('/capabilities');
    renderAdoption(capabilities);
    
    // 加载生命周期漏斗
    renderLifecycleFunnel(capabilities);
}

function renderAdoption(capabilities) {
    const container = document.getElementById('adoption');
    
    const total = capabilities.length;
    const active = capabilities.filter(c => c.current_state === 'ACTIVE').length;
    
    const html = `
        <div>
            <p><strong>Total Capabilities:</strong> ${total}</p>
            <p><strong>Active Capabilities:</strong> ${active}</p>
            <p><strong>Adoption Rate:</strong> ${((active / total) * 100).toFixed(1)}%</p>
        </div>
    `;
    
    container.innerHTML = html;
}

function renderLifecycleFunnel(capabilities) {
    const container = document.getElementById('lifecycle-funnel');
    
    const states = {};
    capabilities.forEach(cap => {
        states[cap.current_state] = (states[cap.current_state] || 0) + 1;
    });
    
    const html = `
        <div>
            ${Object.entries(states).map(([state, count]) => `
                <div style="margin-bottom: 0.5rem;">
                    <strong>${state}:</strong> ${count} capabilities
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

// 工具函数
function getRiskBadgeClass(risk) {
    const map = {
        'LOW': 'success',
        'MEDIUM': 'info',
        'HIGH': 'warning',
        'CRITICAL': 'danger'
    };
    return map[risk] || 'info';
}

function getSeverityBadgeClass(severity) {
    const map = {
        'LOW': 'info',
        'MEDIUM': 'warning',
        'HIGH': 'warning',
        'CRITICAL': 'danger'
    };
    return map[severity] || 'info';
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = `Error: ${message}`;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
}

// 初始化加载
loadTabData('observatory');
