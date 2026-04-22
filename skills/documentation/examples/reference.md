# Reference: `brew()` function

<!-- Quadrant: Reference. Source: https://diataxis.fr/reference/ -->

## Signature

```
brew(leaves: int, water_ml: int, minutes: int, temp_c: int = 100) -> Pot
```

## Parameters

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `leaves` | int | Teaspoons of tea leaves. Range: 1 to 20. | — |
| `water_ml` | int | Volume of water in millilitres. Range: 100 to 3000. | — |
| `minutes` | int | Steep time in minutes. Range: 1 to 10. | — |
| `temp_c` | int | Water temperature in Celsius. Range: 60 to 100. | 100 |

## Returns

A `Pot` object containing the brewed tea. The `Pot` has these fields:

| Field | Type | Description |
|-------|------|-------------|
| `volume_ml` | int | Actual volume of liquid tea, equal to `water_ml`. |
| `strength` | float | Extraction ratio, 0.0 to 1.0. |
| `brewed_at` | datetime | UTC timestamp when brewing completed. |

## Errors

| Error | Condition |
|-------|-----------|
| `ValueError` | Any parameter outside its documented range. |
| `EmptyPotError` | `leaves` is 0. |
| `BoiledDryError` | `water_ml` is 0. |

## See also

- Tutorial: `examples/tutorial.md` — how to use `brew()` for the first time.
- How-to: `examples/how-to.md` — scaling `brew()` for groups.
