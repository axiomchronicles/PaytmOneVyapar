from opentelemetry import metrics

meter = metrics.get_meter("vyapaar.commander")

api_latency = meter.create_histogram("vyapaar.api.duration", unit="ms")
agent_duration = meter.create_histogram("vyapaar.agent.duration", unit="ms")
llm_latency = meter.create_histogram("vyapaar.llm.duration", unit="ms")
llm_tokens = meter.create_counter("vyapaar.llm.tokens")
a2a_latency = meter.create_histogram("vyapaar.a2a.duration", unit="ms")
supplier_latency = meter.create_histogram("vyapaar.supplier.duration", unit="ms")
approval_time = meter.create_histogram("vyapaar.approval.duration", unit="s")
voice_latency = meter.create_histogram("vyapaar.voice.duration", unit="ms")
stt_latency = meter.create_histogram("vyapaar.voice.stt.duration", unit="ms")
tts_latency = meter.create_histogram("vyapaar.voice.tts.duration", unit="ms")
forecast_latency = meter.create_histogram("vyapaar.forecast.duration", unit="ms")
tool_failures = meter.create_counter("vyapaar.tool.failures")
order_failures = meter.create_counter("vyapaar.order.failures")
a2a_failures = meter.create_counter("vyapaar.a2a.failures")
