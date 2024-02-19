from redis_om import JsonModel, EmbeddedJsonModel


class BaseModel(JsonModel):
    class Meta:
        global_key_prefix = "submgr"
        model_key_prefix = "base"


class BaseEmbeddedModel(EmbeddedJsonModel):
    class Meta:
        embedded = True
