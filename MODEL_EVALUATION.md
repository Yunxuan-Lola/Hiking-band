# Public data evaluation

Dataset: SELFBack wrist50, Axivity AX3 wrist accelerometer, downloaded from
https://github.com/rgu-selfback/Datasets (archive commit `3ab9d726a4a10cc46b6a24b11bdd002be8c50d3d`).
Training used 40 subjects and testing used 10 disjoint subjects, with up to 40
evenly spaced windows per recording. Raw data was filtered and resampled to
25 Hz. Each window spans 2 seconds with a 1-second hop. This is one subject-held-out
split, not a guarantee of cross-device performance.

| Output | Public-data source | Precision | Recall | F1 | Test windows |
| --- | --- | ---: | ---: | ---: | ---: |
| climbing | upstairs | 0.622 | 0.775 | 0.690 | 400 |
| idle | sitting, standing | 0.994 | 0.979 | 0.986 | 800 |
| running | jogging | 0.987 | 0.978 | 0.982 | 400 |
| walking | walking | 0.692 | 0.550 | 0.613 | 400 |

Overall window accuracy was 0.852 and macro F1 was 0.818. In the held-out set,
174 of 400 walking windows were classified as climbing. One replay of a walking
window from held-out subject 023 also produced climbing. Model probabilities
are not calibrated confidence guarantees. Since idle combines two source
activities, aggregate accuracy is influenced by its larger test-set weight.

Downstairs was excluded. The dataset does not establish hill-ascent or true
running performance; jogging is a proxy for running and upstairs is a proxy
for climbing. The model was not evaluated on T-Watch hardware, other wearing
orientations, Bluetooth losses, or real-world power consumption. Collect and
label T-Watch data before claiming target-device accuracy. The full generated
report is `RPi/activity_report.json` and the local model is
`RPi/activity_model.pkl`; both are ignored by Git and can be regenerated
using the command in README.
