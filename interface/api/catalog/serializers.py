from rest_framework import serializers

from domain.catalog.entities import NAME_MAX_LENGTH

# Read side quantizes to the two decimals the contract publishes.
PRICE_MAX_DIGITS = 12
PRICE_DECIMAL_PLACES = 2


class ProductSerializer(serializers.Serializer):
    """Read shape. Serializes the domain entity, not the ORM model.

    Exactly the seven fields the contract exposes — created_at is stored but not published.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    # DRF emits Decimal as a JSON string by default. Kept: a JSON number would hand the value
    # to the consumer's float parser and reintroduce the drift exact decimals exist to avoid.
    price = serializers.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=2, read_only=True)
    stock = serializers.IntegerField(read_only=True)
    image_url = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class ProductWriteSerializer(serializers.Serializer):
    """Write shape. Validates STRUCTURE only.

    Business rules (price > 0, stock >= 0, precision) belong to the domain entity, so there is
    deliberately no validate_price here. A shape failure is a 400; a broken rule is a 422.
    """

    name = serializers.CharField(max_length=NAME_MAX_LENGTH, allow_blank=False)
    description = serializers.CharField(allow_blank=True, required=False)
    # decimal_places=None disables DRF's quantization, so the submitted value reaches the
    # entity exactly as written. Quantizing here would silently round "12.345" to "12.35" and
    # rob the domain of the chance to refuse it — the precise failure this design prevents.
    price = serializers.DecimalField(max_digits=None, decimal_places=None)
    stock = serializers.IntegerField(required=False)
    image_url = serializers.URLField(max_length=500, allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False)

    def __init__(self, *args, partial_update: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        if partial_update:
            # PATCH: every field optional, but at least one must be supplied.
            for field in self.fields.values():
                field.required = False

        self._partial_update = partial_update

    def validate(self, attrs):
        if self._partial_update and not attrs:
            raise serializers.ValidationError("Debe indicar al menos un campo a modificar.")

        return attrs
