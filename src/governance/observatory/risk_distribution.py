"""
Risk & Registry Distribution APIs

数据源：
- Capability Registry
- CapabilitySpec (RiskLevel)

保证：
- Registry 是单一数据源
"""

from typing import Dict, List, Any
from collections import defaultdict

from runtime.registry import CapabilityRegistry
from specs.v3.capability_schema import RiskLevel


class RiskDistributionAPI:
    """
    Risk & Registry Distribution API
    
    职责：
    - 从 Registry 读取风险分布
    - 不修改任何数据
    - 100% 只读
    """
    
    def __init__(self, registry: CapabilityRegistry):
        """
        初始化 Risk Distribution API
        
        Args:
            registry: CapabilityRegistry 实例
        """
        self.registry = registry
    
    def get_risk_distribution(self) -> Dict[str, Any]:
        """
        GET /governance/capabilities/risk-distribution
        
        获取风险分布
        
        Returns:
            风险分布字典
        """
        distribution = defaultdict(int)
        capability_ids_by_risk = defaultdict(list)
        
        # 从 Registry 读取所有能力
        for capability_id in self.registry.list_capabilities():
            try:
                spec_dict = self.registry.get_spec(capability_id)
                
                # 提取风险级别
                risk_level = self._extract_risk_level(spec_dict)
                
                distribution[risk_level.value] += 1
                capability_ids_by_risk[risk_level.value].append(capability_id)
            except Exception as e:
                # 记录错误但继续处理
                print(f"⚠️  Failed to get risk for {capability_id}: {e}")
        
        return {
            "distribution": dict(distribution),
            "total": sum(distribution.values()),
            "by_risk": dict(capability_ids_by_risk)
        }
    
    def get_capabilities_by_risk(self, risk_level: RiskLevel) -> List[str]:
        """
        GET /governance/capabilities/by-risk?risk={level}
        
        按风险级别获取能力列表
        
        Args:
            risk_level: 风险级别
        
        Returns:
            能力 ID 列表
        """
        capability_ids = []
        
        for capability_id in self.registry.list_capabilities():
            try:
                spec_dict = self.registry.get_spec(capability_id)
                spec_risk_level = self._extract_risk_level(spec_dict)
                
                if spec_risk_level == risk_level:
                    capability_ids.append(capability_id)
            except Exception as e:
                print(f"⚠️  Failed to get risk for {capability_id}: {e}")
        
        return capability_ids
    
    def _extract_risk_level(self, spec_dict: Dict) -> RiskLevel:
        """
        从 spec_dict 提取风险级别
        
        Args:
            spec_dict: 能力规范字典
        
        Returns:
            RiskLevel 枚举
        """
        # 尝试多种可能的路径
        if "risk" in spec_dict:
            risk_data = spec_dict["risk"]
            if isinstance(risk_data, dict):
                level_str = risk_data.get("level")
            else:
                level_str = str(risk_data)
            
            if level_str:
                try:
                    return RiskLevel(level_str)
                except ValueError:
                    pass
        
        # 默认返回 MEDIUM
        return RiskLevel.MEDIUM
