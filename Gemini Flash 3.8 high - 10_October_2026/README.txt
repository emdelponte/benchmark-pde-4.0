******************************** FUSARIUM HEAD BLIGHT DATA MATRIX******************************

                              VERSION 2.1.0

SUMMARY OF CHANGES FROM VERSION 2.0.0
- Added: parquet file of the data; YAML data dictionary. The parquet file can be read using the arrow::read_parquet() function, which will preserve the factor variables such as resist.
- Fixed: descriptions for MINMAXDIFF variables, T.14T22.CD.1, T.14T22.CD.2 and T1510 in the pdf and html data dictionaries.
- Unchanged: data values, variable names, types, csv/rds files.                               
                              
                              VERSION 2.0.0
                              

SUMMARY OF CHANGES FROM VERSION 1.0.0:
- New FHB observations were added, expanding the data matrix from 527 to 999 rows. 
- All weather data were sourced from, using Wolfram Mathematica's WeatherData function, the nearest standard weather station (including citizen weather stations) to the field plot.
- Weather data and flowering date were all in UTC, not adjusted to local time zone. 

- New weather-based variables have been added, and others that were found to be uninformative for prediction were removed. 
- A new variable-naming nomenclature was adopted to standardize the naming of the weather-based variables. Hence the weather-based variables in Version 1.0.0 have been renamed, except for variables that had been first described in the De Wolf et al. (2003) paper (https://doi.org/10.1094/PHYTO.2003.93.4.428), for which their orginal names were retained for backward consistency.


INTRODUCTION:
Fusarium head blight severity was evaluated in fungicide-untreated plots maintained by collaborators participating in projects funded by the U.S. Wheat & Barley Scab Initiative (USWBSI). There are 999 rows, representing data collected from 1982-2015 in 17 states. 

The field-based observations were linked to weather variables summarizing conditions in pre- and post-anthesis windows relative to anthesis (flowering) date. Weather data were obtained from the closest standard weather station (reporting data within the required time period) to the field plot and were accessed via scripts making use of Mathematica's WeatherData function. This approach, instead of getting weather data from the collaborators themeselves, gave us better quality control and verification of weather data source.

The anthesis reference point is 00 UTC on the flowering date.

For weather variable creation, a 24 h day was defined as 00 UTC to 23 UTC.
A 12 h daily period was defined as from 20 UTC to 07 UTC.


ABBREVIATIONS:
These are used in the variable-naming nomenclature and in the descriptions of the variables.

T =  air temperature 
D = dewpoint
TDD (or DD) = temperature-dewpoint depression
P = barometric pressure 
RH = relative humidity
VPD = vapor pressure deficit
A = average or mean
sd = standard deviation
hr = hours
d = days
No. hr = number of hours
No. d = number of days
PRE = pre-anthesis
POST = post-anthesis


META-DATA ON THE WEATHER-BASED VARIABLES:
origin:
- The paper in which the variable was first used and/or described.
    * DeWolf et al. (2003): https://doi.org/10.1094/PHYTO.2003.93.4.428
    * Shah et al. (2013): https://doi.org/10.1094/PHYTO-11-12-0304-R
    * Shah et al. (2019): https://doi.org/10.1098/rstb.2018.0273
    * Shah et al. (2021): https://doi.org/10.1371/journal.pcbi.1008831 

variable_type:
- A codification of what the variable summarizes.

variable_name:
- The name ascribed to the variable.

summary:
- A description of what exactly the variable summarizes.

period:
- pre = pre-anthesis, post = post-anthesis, pre-post = starts pre and ends post.

type:
- The type of weather time series being summarized 
T = temperature
D = dewpoint
P = pressure
RH = relative humidity
VPD = vapor pressure deficit
TDD (DD) = temperature-dewpoint depression
TRH = combinations of temperature and relative humidity conditions

metric:
- Whether the variable is a mean or a count.

time_step:
- Whether the variable summarizes over hourly or daily time steps (e.g., count of number of hours, or a daily mean).

day:
- Whether the summary is over the overnight (12 hr) or full day (24 hr period). 

win_start_day:
- The start day (relative to anthesis) of the window the variable summarizes. 

win_start_period:
- Whether the window start day is in the pre-anthesis or post-anthesis period, or at anthesis.

win_end_day:
- The end day of the window the variable summarizes. 

win_end_period:
- Whether the window end day is in the pre-anthesis or post-anthesis period, or at anthesis. 

win_length:
- The length (in days) of the window.



********************************** CONTENTS ***********************************
1.  README.txt 
- This file.

2.  FHBVer2.csv
- A comma-delimited text file with 999 observation rows and 337 columns. Column headers are in row 1. 
- missing data are coded as NA.

3.  FHBVer2.rds
- the data matrix saved as an R RDS file.

4.  FHBVer2Codebook.pdf 
- a human-readable summary of the variables in the dataset and their descriptions. 

5.   FHBVer2Codebook.html 
- a machine-readable summary of the variables in the dataset and their descriptions. 

6.  VariablesMetaData.csv
- A comma-delimited text file with meta-data on the weather-based variables. Column headers are in row 1.

7.  VariablesMetaData.rds
- An R RDS file containing the meta-data on the weather-based variables.



********************************* CONTACT INFORMATION **********************************
Denis A. Shah
e-mail: dashah81@ksu.edu

Erick D. De Wolf
e-mail: dewolf1@ksu.edu

Pierce A. Paul
e-mail: paul.661@osu.edu

Laurence V. Madden
e-mail: madden.1@osu.edu




***************************** ACKNOWLEDGEMENTS ********************************
Funding for this work was provided by the U.S. Wheat & Barley Scab Initiative (USWBSI).

