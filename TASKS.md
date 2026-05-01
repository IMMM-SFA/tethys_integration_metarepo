# Tasks and open discussion

Running task tracker and domain-level discussion log for the metarepo.
See `README.md` for repo overview, `PIPELINE.md` for how to run things,
and `docs/CLEANUP.md` for the recent scripts/ reorganization rationale.

## Tasks

 - [ ] Issue with regridding in Tethys https://github.com/JGCRI/tethys/issues/71. Assignee: Chris
 - [ ] Get Hassan running on Tethys (importlib issue). Assignee: Travis, Hassan
 - [ ] Decide how to disaggregate renewable vs fossil water, see below. Assignee: Hassan and all.
 - [ ] Pilot disaggregation code within Tethys. Assignee: Hassan.
 - [ ] Consider if there is a data-driven strategy for renewable/fossil disaggregation. Low priority, but keep an eye out for data. Assignee: Cameron.
 - [ ] Check with Kanishka about the historical LULC data layer. Assignee: Travis.
 - [ ] Run Tethys for the historical period with current tethys but updated GCAM. Assignee: Travis and Hassan.
 - [ ] Investigate the latest USGS water usage data and compare with historical Tethys output. Assignee: Cameron.
 - [x] Provide updated population data. What about historical population? Assignee: Chris. [PR #1](https://github.com/IMMM-SFA/tethys_integration_metarepo/pull/1)
 - [ ] Implement GO-CERF-GO temporal electricity sector downscaling. Assignee: Hassan.
 - [ ] Read the Isaac paper draft and decide how to move it forward. Assignee: Cameron.
 - [ ] Update Tethys in support of these decisions. Assignee: Hassan, Travis.
 - [ ] Connect with the USGS to see if there are other datasets we could leverage (within the IHTM network for instance). TBD once we are farther along.
 - [ ] ADD ALL CODE AND WORKFLOW TO THIS METAREPO. Assignee: all.

## Discussion topics

What data/years to use for "historical" scenario? There is no official historical GCAM-USA run, and the 1975-2015 data within GCAM-USA outputs is not necessarily trustworthy.

How does Tethys handle missing years? I think it just linearly interpolates, is that okay? In particular for the historical run this is relevant since GCAM-USA only provides [1975, 1990, 2005, 2010, 2015, 2020], and 2020 is technically simulated under the future scenario settings.

GCAM-USA, Tethys, mosartwmpy, USGS potentially have different strategies of reporting water usage regarding the location of withdrawal vs the location of delivery/consumption. What problems does this cause and how do we deal with them?

Which population and land use should we use for the historical scenario?

What units does Tethys/GCAM-USA report in? I think it's km^3.

### Renewable vs fossil water disaggregation

GCAM-USA reports renewable vs fossil water usage at the basin level but does not disaggregate by sector.

Hassan proposes to apply the basin-level shares to all cells within the basin, excepting that electricity sector will only use renewable water.

However, we would still want to restrict fossil water usage to grid cells that could conceivably access it. Ideas include using data from Superwell or Jim Yoon or other sources to obtain binary gridded fossil water availability maps.

Such strategies would then need to be implemented into Tethys.

In-depth proposal document: https://pnnl-my.sharepoint.com/:w:/g/personal/hassan_niazi_pnnl_gov/EYcftCLewBpDgnc8mHZp2vcB5SE8A7jN4zT-R9-9PHEDzA?e=5JiX8E
