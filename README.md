# Install and Run

## System requirements

- [Docker Compose 1.29.2+](https://docs.docker.com/compose/install/), earlier versions may also work
- Linux or MacOS - only tested on Ubuntu, but should work on Mac.

## Starting the application

Execute the following to run the app:

```
$ docker-compose build && docker-compose up
```

`sudo` or similar privlege escalation may be required depending on your system.

If successful, you'll see logs for two services come up without errors `grafana_1` and `postgres_1`

`tagup_app_1` will take a few minutes to ingest and clean the provided data. When it completes, it will log `Machine data ingest complete!` to the console.

## Examining the data

Grafana is provided as a visualization tool for the user. Connection to the database and a basic dashboard come default.

Grafana will start at [`http://localhost:3000`](http://localhost:3000) by default.

Navigate to [`http://localhost:3000/dashboards`](http://localhost:3000/dashboards) and select the first item in the list to access the provided dashboard.

# Technical decisions and architecture

## Decision factors

I approached technology and scoping decisions made in this project balancing the following factors:

- Limited understanding of the customer's use cases led me to opt for simpler, more general technolgies rather than their potentially higher-performance counterparts. I didn't see a need for heavy optimization in many cases.

- Some tools may be a better fit for a real production deployments but those tools tend to also be tricky to configure and need a lot of fuss. To reduce complexity, I tended to opt for tools that came with batteries already installed.

- My existing skill set: There may be better tools for the job, but learning technologies outside my existing range would take too long for a project of this scope.

- Running on a local machine: I made tradeoffs on technologies for this demo because I wanted it to be locally runnable by others. There may be better suited cloud-based options, but it would have expanded complexity and limited usability of the final demo. Specific tradeoffs I made are discussed below.

## Python

The problem called for simple CSV loading, transformation, and insertion into a database. Python has great built-in support for CSV management, an easy-to-use Postgres connector in `psycopg2` and - compared to other languages in my toolset - requires little boilerplate to get an application going.

My Python ecosystem knowledge isn't up to modern application standards - I use it for scripting exclusively - but I'm always confident I can blitz out a valuable script with it.

## Postgres

Postgres wasn't my first choice. I would have preferred to use a columnar database like RedShift or Snowflake due to the primary use case of this application being to asynchronous analysis rather than OLTP or streaming applications.

Alas, I wanted to run all locally so the two columnar stores I'm experienced in weren't options.

Postgres is well known, well supported, and still a very good option for some OLAP workloads. I've used it within docker-compose before for other toy projects and knew it would be quick while also being a more than capable production option as well. I didn't use it here, but this application would have been a nice use case for its table partitioning feature as well.

## Grafana

Visualizations for timeseries data are critical. They make it simple for a dev to visually debug their queries, and a quick and dirty way to convey information to an end user.

Writing a web UI for timeseries visualization would have been possible, but quite an undertaking. I'm sure there are some end user friendly options for visualizing timeseries data, but I've worked with Grafana in the past. I was already familiar with its wide range of datasource capabilities and knew I'd be able to get something that looks pretty nice in a short period of time.

Its not the most non-technical user friendly interface, but the flexibility it enables for users is killer.

## Docker Compose

I wanted to run everything locally, and I wanted to make it painless for someone else to do the same. Docker is the obvious solution to ship an environment these days, and Docker Compose is the easiest way I know to orchestrate containers locally.

Since most people already have docker on their system, theres a good chance they already have compose and if not, the installation should be straight-forward.

There are some solutions out there for local kubernetes that can do live-reloads and more advanced caching, restarting, and networking, but kubernetes is just too much overhead for a demo. Unless you have already written the YAML for a production cluster that you can reuse, there's too much to fuss with locally.

## Application

### Data Loading

The application accepts a path argument to a directory with CSVs in it. This argument is hard-coded in the `docker-compose.yml` file for purposes for quickly getting running, but the container itself can process from any path

After some validation on the path, for each file we read each row and insert its contents into Postgres. I used a Python generator to only require a single row to be in-memory at a time. Given the size of the dataset reading it into memory wouldn't have been a problem, but I thought it would be non-risky optimization to make.

### DB Schema

I was debating between two schemas. I went with the following:

```sql
create table if not exists machine_metrics (
    machine_name varchar(64) not null,
    time timestamp not null,
    metric_1 double precision,
    metric_2 double precision,
    metric_3 double precision,
    metric_4 double precision
);
```

The alternative was more like a true timeseries DB might store it. More general, likely more performant for timeseries operations, but loosens the relationship between the metrics coming from a single machine, and getting the indexes right is a little more tricky:

```sql
create table if not exists machine_metrics (
    time timestamp not null,
    labels jsonb, // eg { metric: 'metric_1', machine: 'machine_1'}
    value double precision
);
```

I went with the former because it kept the data simple, close to its original form, and for an OLAP use case I thought it would be more future proof.

### Data Cleaning

There were a number of outliers in each timeseries that needed removal. I calculated the [interquartile range](https://en.wikipedia.org/wiki/Interquartile_range#Outliers) for each timeseries and used it to eliminate most outliers.

Since each machine's data reflects a failure at some point in time, calculating outliers using the near-zero data points was causing valid data to be excluded (eg some thresholds were +-0.03). To compensate I excluded near-zero data points from the IRQ calculation.

Similarly, some machines would encounter a failure very early in their timseries. After exlcuding the near-zero points, these timeseries would have a majority of their data be outlier points (in the realm of `250` or so). To compensate, I excluded all values above 225 and below -225 when calculating the IRQ.

Since each machine's normal operating values seemed to be within similar ranges, it seemed reasonable to apply these arbritrary caps. If new machine models were to be handled by an application or if value magnitude were to become different, these bounds would need to be handled

# Data Discussion

Upon examination of the data, each machine exhibits a period of stable, wave-like behavior. This period is much longer for some machines than others.

For each machine there is a clear failure point at which each metric falls to a near-zero value.

![Failure point](/images/no-increase.png)

In some cases, but not all metrics will become more sporadic and increase in amplitude in the time leading up to a failure.

![Sporadic failure](/images/amplitude-increase.png)

Not all metrics will show the same instability characteristics in lead up to a failure. Metric #3 seems to not vary in amplitude as much as other metrics from the same machine. If anything it reduces in intensity and its cycle time gets shorter.

![Metric 3 more stable?](/images/all-metrics.png)
