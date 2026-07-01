# YOLO People Models

Store trained people-counting model files here.

Expected deployment model:

```text
best.pt
```

The model should detect one class:

```text
person
```

The dashboard or AI vision service will count detected `person` boxes and post
the count to:

```text
POST /api/ai-count
{"people": 4}
```
