"""
Runtime Engine - Core execution orchestrator.

This module provides the main execution engine that coordinates all runtime components.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .types import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    UndoRecord,
    ActionOutput,
    ConfirmationDeniedError,
    CapabilityNotFoundError,
    ValidationError,
    SecurityError,
)
from .registry import CapabilityRegistry
from .handler import ActionHandler
from .undo.manager import UndoManager
from .audit import AuditLogger

# Governance integration (optional)
try:
    from governance.lifecycle.lifecycle_service import LifecycleService
    from governance.lifecycle.enforcement import GovernanceViolation, enforce_lifecycle_state
    from governance.signals.signal_bus import SignalBus
    from governance.signals.models import SignalType, SignalSeverity, SignalSource
    GOVERNANCE_AVAILABLE = True
except ImportError:
    GOVERNANCE_AVAILABLE = False
    LifecycleService = None
    SignalBus = None
    GovernanceViolation = Exception
    enforce_lifecycle_state = None


class RuntimeEngine:
    """
    Main execution orchestrator for AI-First Runtime.
    
    This class coordinates the execution flow:
    1. Validate capability exists
    2. Validate parameters
    3. Check security constraints
    4. Request confirmation if needed
    5. Execute handler
    6. Create and push undo record
    7. Return result
    """
    
    def __init__(
        self, 
        registry: CapabilityRegistry, 
        undo_manager: Optional[UndoManager] = None, 
        audit_logger: Optional[AuditLogger] = None,
        lifecycle_service: Optional['LifecycleService'] = None,
        signal_bus: Optional['SignalBus'] = None
    ):
        """
        Initialize runtime engine.
        
        Args:
            registry: CapabilityRegistry instance
            undo_manager: Optional UndoManager for operation rollback
            audit_logger: Optional AuditLogger for compliance logging
            lifecycle_service: Optional LifecycleService for governance
            signal_bus: Optional SignalBus for governance signals
        """
        self.registry = registry
        self.undo_manager = undo_manager
        self.audit_logger = audit_logger
        self.lifecycle_service = lifecycle_service
        self.signal_bus = signal_bus
        self._execution_count = 0
    
    def execute(
        self,
        capability_id: str,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Execute a capability with given parameters.
        
        This is the main entry point for capability execution.
        
        Args:
            capability_id: ID of capability to execute
            params: Input parameters
            context: Execution context
        
        Returns:
            ExecutionResult with outputs and status
        """
        start_time = time.time()
        self._execution_count += 1
        
        try:
            # Step 0: Check governance (if available) - 强制执行生命周期状态
            if self.lifecycle_service:
                try:
                    enforce_lifecycle_state(self.lifecycle_service, capability_id)
                except GovernanceViolation as e:
                    # Emit GOVERNANCE_REJECTED signal
                    if self.signal_bus:
                        self.signal_bus.append(
                            capability_id=capability_id,
                            signal_type=SignalType.GOVERNANCE_REJECTED,
                            severity=SignalSeverity.CRITICAL,
                            source=SignalSource.RUNTIME,
                            workflow_id=context.session_id,
                            metadata={
                                "reason": str(e),
                                "state": self.lifecycle_service.get_state(capability_id).value
                            }
                        )
                    # Hard rejection - 治理违规
                    return ExecutionResult(
                        capability_id=capability_id,
                        status=ExecutionStatus.ERROR,
                        outputs={},
                        error_message=str(e),
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
            
            # Step 1: Get handler
            try:
                handler = self.registry.get_handler(capability_id)
            except Exception as e:
                # Emit CAPABILITY_NOT_FOUND signal
                if self.signal_bus:
                    self.signal_bus.append(
                        capability_id=capability_id,
                        signal_type=SignalType.CAPABILITY_NOT_FOUND,
                        severity=SignalSeverity.HIGH,
                        source=SignalSource.RUNTIME,
                        workflow_id=context.session_id,
                        metadata={"error": str(e)}
                    )
                raise
            
            # Step 2: Validate parameters
            handler.validate_params(params)
            
            # Step 3: Check confirmation requirement
            if handler.requires_confirmation():
                if not self._request_confirmation(handler, params, context):
                    return ExecutionResult(
                        capability_id=capability_id,
                        status=ExecutionStatus.DENIED,
                        outputs={},
                        error_message="User denied confirmation",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
            
            # Step 4: Execute handler (returns ActionOutput or dict for backward compatibility)
            try:
                result = handler.execute(params, context)
                
                # Emit success signal
                if self.signal_bus:
                    self.signal_bus.append(
                        capability_id=capability_id,
                        signal_type=SignalType.EXECUTION_SUCCESS,
                        severity=SignalSeverity.LOW,
                        source=SignalSource.RUNTIME,
                        workflow_id=context.session_id,
                        metadata={}
                    )
            except Exception as e:
                # Emit failure signal
                if self.signal_bus:
                    self.signal_bus.append(
                        capability_id=capability_id,
                        signal_type=SignalType.EXECUTION_FAILED,
                        severity=SignalSeverity.MEDIUM,
                        source=SignalSource.RUNTIME,
                        workflow_id=context.session_id,
                        metadata={"error": str(e), "error_type": type(e).__name__}
                    )
                raise
            
            # Intelligent Adapter: Auto-wrap dict to ActionOutput for read-only operations
            if isinstance(result, dict):
                # Check if this is a destructive operation
                side_effects = handler.contracts.get("side_effects", [])
                is_read_only = len(side_effects) == 0 or side_effects == ["read_only"]
                
                if not is_read_only:
                    # CRITICAL: Destructive operations MUST return ActionOutput with undo_closure
                    raise RuntimeError(
                        f"Handler {capability_id} has side effects {side_effects} but returned dict instead of ActionOutput. "
                        f"Destructive handlers MUST return ActionOutput with undo_closure for safety."
                    )
                
                # Safe: Read-only operation, auto-wrap
                action_output = ActionOutput(
                    result=result,
                    undo_closure=None,
                    description=f"Executed {capability_id} (read-only)"
                )
            else:
                action_output = result
            
            # Step 5: Create undo record if available
            undo_record = None
            if context.undo_enabled and action_output.undo_closure:
                operation_id = f"{capability_id}_{uuid.uuid4().hex[:8]}"
                undo_record = UndoRecord(
                    operation_id=operation_id,
                    capability_id=capability_id,
                    timestamp=datetime.now(),
                    params=params,
                    undo_function=action_output.undo_closure,
                    undo_args={},  # Closure captures everything
                    description=action_output.description or f"Executed {capability_id}",
                )
                
                # Push to undo manager if available (RuntimeEngine's responsibility)
                if self.undo_manager is not None:
                    self.undo_manager.push(undo_record)
            
            # Step 6: Create success result
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                capability_id=capability_id,
                status=ExecutionStatus.SUCCESS,
                outputs=action_output.result,
                execution_time_ms=execution_time_ms,
                undo_available=undo_record is not None,
                undo_record=undo_record,
                metadata={
                    "execution_number": self._execution_count,
                    "handler_version": handler.version,
                },
            )
            
            # Step 7: Log to audit (if enabled)
            if self.audit_logger is not None:
                side_effects = handler.contracts.get("side_effects", [])
                self.audit_logger.log_action(
                    session_id=context.session_id,
                    user_id=context.user_id,
                    capability_id=capability_id,
                    action_type="execute",
                    params=params,
                    result=action_output.result,
                    status="success",
                    side_effects=side_effects,
                    requires_confirmation=handler.requires_confirmation(),
                    was_confirmed=True if handler.requires_confirmation() else None,
                    undo_available=undo_record is not None,
                    duration_ms=int(execution_time_ms),
                )
            
            return result
        
        except CapabilityNotFoundError as e:
            return self._create_error_result(
                capability_id, str(e), start_time, ExecutionStatus.ERROR
            )
        
        except ValidationError as e:
            return self._create_error_result(
                capability_id, f"Validation error: {e}", start_time, ExecutionStatus.FAILED
            )
        
        except SecurityError as e:
            return self._create_error_result(
                capability_id, f"Security error: {e}", start_time, ExecutionStatus.FAILED
            )
        
        except ConfirmationDeniedError as e:
            return self._create_error_result(
                capability_id, str(e), start_time, ExecutionStatus.DENIED
            )
        
        except Exception as e:
            return self._create_error_result(
                capability_id, f"Execution failed: {e}", start_time, ExecutionStatus.ERROR
            )
    
    def _request_confirmation(
        self,
        handler: ActionHandler,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> bool:
        """
        Request user confirmation for dangerous operation.
        
        Args:
            handler: ActionHandler instance
            params: Execution parameters
            context: Execution context
        
        Returns:
            True if confirmed, False if denied
        """
        if context.confirmation_callback is None:
            # No callback provided, auto-deny dangerous operations
            return False
        
        # Prepare confirmation message
        message = self._format_confirmation_message(handler, params)
        
        # Call confirmation callback
        try:
            return context.confirmation_callback(message, params)
        except Exception as e:
            print(f"⚠️  Confirmation callback failed: {e}")
            return False
    
    def _format_confirmation_message(
        self,
        handler: ActionHandler,
        params: Dict[str, Any],
    ) -> str:
        """
        Format confirmation message for user.
        
        Args:
            handler: ActionHandler instance
            params: Execution parameters
        
        Returns:
            Formatted message string
        """
        lines = [
            f"⚠️  CONFIRMATION REQUIRED",
            f"",
            f"Capability: {handler.capability_id}",
            f"Description: {handler.get_description()}",
            f"Side Effects: {', '.join(handler.get_side_effects())}",
            f"",
            f"Parameters:",
        ]
        
        for key, value in params.items():
            lines.append(f"  {key}: {value}")
        
        lines.extend([
            f"",
            f"Undo Strategy: {handler.get_undo_strategy()}",
            f"",
            f"Proceed with this operation?",
        ])
        
        return "\n".join(lines)
    
    def _has_side_effects(self, handler: ActionHandler) -> bool:
        """
        Check if handler has side effects (not read-only).
        
        Args:
            handler: ActionHandler instance
        
        Returns:
            True if has side effects
        """
        side_effects = handler.get_side_effects()
        return len(side_effects) > 0 and side_effects != ["read_only"]
    
    def _create_error_result(
        self,
        capability_id: str,
        error_message: str,
        start_time: float,
        status: ExecutionStatus = ExecutionStatus.ERROR,
    ) -> ExecutionResult:
        """
        Create error result.
        
        Args:
            capability_id: Capability ID
            error_message: Error description
            start_time: Execution start time
            status: Execution status
        
        Returns:
            ExecutionResult with error
        """
        execution_time_ms = (time.time() - start_time) * 1000
        
        result = ExecutionResult(
            capability_id=capability_id,
            status=status,
            outputs={},
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            undo_available=False,
        )
        
        # Log error to audit (if enabled)
        # Note: We don't have context here, so we skip audit logging for errors
        # This is acceptable since errors are already logged via standard logging
        
        return result
    
    def get_execution_count(self) -> int:
        """
        Get total number of executions.
        
        Returns:
            Execution count
        """
        return self._execution_count
    
    def reset_execution_count(self) -> None:
        """Reset execution counter"""
        self._execution_count = 0
    
    def list_capabilities(self) -> list:
        """
        List all available capabilities.
        
        Returns:
            List of capability IDs
        """
        return self.registry.list_capabilities()
    
    def get_capability_info(self, capability_id: str) -> Dict[str, Any]:
        """
        Get information about a capability.
        
        Args:
            capability_id: Capability ID
        
        Returns:
            Capability information dictionary
        """
        handler = self.registry.get_handler(capability_id)
        return handler.to_info_dict()
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"<RuntimeEngine: {len(self.registry)} capabilities, "
            f"{self._execution_count} executions>"
        )
