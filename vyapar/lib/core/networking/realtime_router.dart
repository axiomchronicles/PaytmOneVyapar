enum RealtimeTarget {
  all,
  auth,
  inventory,
  recommendations,
  analytics,
  approvals,
  orders,
  suppliers,
  negotiations,
  a2a,
  notifications,
}

abstract final class RealtimeEventRouter {
  static Set<RealtimeTarget> targets(String eventType) => switch (eventType) {
    'REALTIME_AUTH_FAILED' => {RealtimeTarget.auth},
    'REALTIME_RESYNC_REQUIRED' => {RealtimeTarget.all},
    'INVENTORY_LOW' || 'INVENTORY_UPDATED' || 'DEMAND_SURGE_DETECTED' => {
      RealtimeTarget.inventory,
      RealtimeTarget.recommendations,
      RealtimeTarget.analytics,
    },
    'APPROVAL_REQUIRED' || 'APPROVAL_GRANTED' || 'APPROVAL_REJECTED' => {
      RealtimeTarget.approvals,
      RealtimeTarget.orders,
      RealtimeTarget.notifications,
    },
    'ORDER_EXECUTED' || 'ORDER_FAILED' || 'SUPPLIER_CONFIRMATION_RECEIVED' => {
      RealtimeTarget.orders,
      RealtimeTarget.analytics,
      RealtimeTarget.notifications,
    },
    'NEGOTIATION_UPDATED' => {RealtimeTarget.negotiations, RealtimeTarget.a2a},
    'A2A_MESSAGE_RECEIVED' => {RealtimeTarget.a2a},
    'NOTIFICATION_CREATED' => {RealtimeTarget.notifications},
    _ => const {},
  };
}
