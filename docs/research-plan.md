# Prithvi compatibility review and experiment plan

The official NASA/IBM repository and flood configuration were read; no large
weights were downloaded and no Prithvi benchmark was run.

Sources:
- https://github.com/NASA-IMPACT/Prithvi-EO-2.0
- https://github.com/NASA-IMPACT/Prithvi-EO-2.0/blob/main/configs/sen1floods11.yaml

The published flood example uses six **optical** bands: BLUE, GREEN, RED,
NIR_NARROW, SWIR_1 and SWIR_2. For the 13-band Sen1Floods11 S2 stack these are
1-based indices 2, 3, 4, 9, 12 and 13. Its input reflectance scale is 0.0001,
labels ignore −1, and examples resize to 224×224. This is not a drop-in replacement
for this app's two-band radar model. The config has placeholders for data/backbone,
`backbone_pretrained: false`, and different feature indices for 100M/300M/600M
models; it must be deliberately configured before any pretrained comparison.
The README lists 300M and 600M variants, substantially larger than this baseline.

A scientifically defensible comparison should:

1. First complete the small event-disjoint radar baseline and document failures.
2. Prepare identical event splits and cloud/invalid masks for the optical inputs.
3. Train a six-band optical U-Net control as well as the selected Prithvi model.
   Comparing only optical Prithvi to radar U-Net confounds architecture with sensor.
4. Tune only on validation events. Report per-event held-out IoU, precision,
   recall, Dice, failure examples, inference time and peak memory on named hardware.
5. Use identical valid evaluation pixels and document resizing/resampling effects.
6. Calibrate confidence separately if needed; sigmoid values are not calibrated
   uncertainty. Test any before/after water reference before calling water flooding.

No superiority, speed benefit, geographic generalization, or uncertainty quality
has been established. Cloud-domain access and a suitable compute plan are needed
before this experiment. A Mac CPU demo does not imply that large-model fine-tuning
is feasible or inexpensive.
