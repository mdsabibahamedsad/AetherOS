# AetherOS Performance Benchmark Report
Generated: Sat Sep 12 10:06:05 2026
Total benchmarks: 12

## cli

### CLI Cold Startup (PERF-CLI-001)
Status: MEASURED
Iterations: 10 (warmup: 3)
- exit_code_max: 0.000 
- exit_code_mean: 0.000 
- exit_code_median: 0.000 
- exit_code_min: 0.000 
- exit_code_stdev: 0.000 
- startup_time_ms_max: 2365.803 
- startup_time_ms_mean: 1244.052 
- startup_time_ms_median: 963.519 
- startup_time_ms_min: 862.654 
- startup_time_ms_stdev: 510.125 
- stdout_bytes_max: 15345.000 
- stdout_bytes_mean: 15345.000 
- stdout_bytes_median: 15345.000 
- stdout_bytes_min: 15345.000 
- stdout_bytes_stdev: 0.000 

### CLI Cold Startup (PERF-CLI-001)
Status: MEASURED
Iterations: 10 (warmup: 3)
- exit_code_max: 0.000 
- exit_code_mean: 0.000 
- exit_code_median: 0.000 
- exit_code_min: 0.000 
- exit_code_stdev: 0.000 
- startup_time_ms_max: 974.212 
- startup_time_ms_mean: 838.751 
- startup_time_ms_median: 822.871 
- startup_time_ms_min: 811.415 
- startup_time_ms_stdev: 48.242 
- stdout_bytes_max: 15345.000 
- stdout_bytes_mean: 15345.000 
- stdout_bytes_median: 15345.000 
- stdout_bytes_min: 15345.000 
- stdout_bytes_stdev: 0.000 

### CLI Command Dispatch (PERF-CLI-002)
Status: MEASURED
Iterations: 20 (warmup: 5)
- cmd_--help_ms_max: 908.418 
- cmd_--help_ms_mean: 883.755 
- cmd_--help_ms_median: 885.719 
- cmd_--help_ms_min: 862.075 
- cmd_--help_ms_p50: 888.567 
- cmd_--help_ms_p95: 908.418 
- cmd_--help_ms_p99: 908.418 
- cmd_--help_ms_stdev: 13.138 
- cmd_config_show_ms_max: 1062.332 
- cmd_config_show_ms_mean: 1038.600 
- cmd_config_show_ms_median: 1036.971 
- cmd_config_show_ms_min: 1017.187 
- cmd_config_show_ms_p50: 1037.792 
- cmd_config_show_ms_p95: 1062.332 
- cmd_config_show_ms_p99: 1062.332 
- cmd_config_show_ms_stdev: 12.808 
- cmd_skills_list_ms_max: 1968.554 
- cmd_skills_list_ms_mean: 1160.271 
- cmd_skills_list_ms_median: 1105.436 
- cmd_skills_list_ms_min: 1072.429 
- cmd_skills_list_ms_p50: 1114.755 
- cmd_skills_list_ms_p95: 1968.554 
- cmd_skills_list_ms_p99: 1968.554 
- cmd_skills_list_ms_stdev: 198.260 

## database

### SQLite Connection Acquisition (PERF-DATABASE-001)
Status: MEASURED
Iterations: 50 (warmup: 10)
- connection_time_ms_max: 1.130 
- connection_time_ms_mean: 0.194 
- connection_time_ms_median: 0.167 
- connection_time_ms_min: 0.160 
- connection_time_ms_p50: 0.167 
- connection_time_ms_p95: 0.235 
- connection_time_ms_p99: 1.130 
- connection_time_ms_stdev: 0.137 

### SQLite Query Performance (PERF-DATABASE-002)
Status: MEASURED
Iterations: 30 (warmup: 5)
- fullscan_100000_ms_max: 10.996 
- fullscan_100000_ms_mean: 8.201 
- fullscan_100000_ms_median: 8.010 
- fullscan_100000_ms_min: 7.559 
- fullscan_100000_ms_p50: 8.025 
- fullscan_100000_ms_p95: 9.158 
- fullscan_100000_ms_p99: 10.996 
- fullscan_100000_ms_stdev: 0.664 
- fullscan_10000_ms_max: 10.422 
- fullscan_10000_ms_mean: 8.293 
- fullscan_10000_ms_median: 8.176 
- fullscan_10000_ms_min: 7.695 
- fullscan_10000_ms_p50: 8.180 
- fullscan_10000_ms_p95: 9.380 
- fullscan_10000_ms_p99: 10.422 
- fullscan_10000_ms_stdev: 0.555 
- fullscan_1000_ms_max: 9.805 
- fullscan_1000_ms_mean: 8.261 
- fullscan_1000_ms_median: 8.169 
- fullscan_1000_ms_min: 7.637 
- fullscan_1000_ms_p50: 8.179 
- fullscan_1000_ms_p95: 9.540 
- fullscan_1000_ms_p99: 9.805 
- fullscan_1000_ms_stdev: 0.523 
- fullscan_100_ms_max: 10.706 
- fullscan_100_ms_mean: 9.039 
- fullscan_100_ms_median: 8.726 
- fullscan_100_ms_min: 8.394 
- fullscan_100_ms_p50: 8.736 
- fullscan_100_ms_p95: 10.630 
- fullscan_100_ms_p99: 10.706 
- fullscan_100_ms_stdev: 0.632 
- point_query_100000_ms_max: 0.183 
- point_query_100000_ms_mean: 0.118 
- point_query_100000_ms_median: 0.113 
- point_query_100000_ms_min: 0.076 
- point_query_100000_ms_p50: 0.115 
- point_query_100000_ms_p95: 0.179 
- point_query_100000_ms_p99: 0.183 
- point_query_100000_ms_stdev: 0.034 
- point_query_10000_ms_max: 0.232 
- point_query_10000_ms_mean: 0.125 
- point_query_10000_ms_median: 0.117 
- point_query_10000_ms_min: 0.077 
- point_query_10000_ms_p50: 0.122 
- point_query_10000_ms_p95: 0.227 
- point_query_10000_ms_p99: 0.232 
- point_query_10000_ms_stdev: 0.043 
- point_query_1000_ms_max: 0.258 
- point_query_1000_ms_mean: 0.126 
- point_query_1000_ms_median: 0.113 
- point_query_1000_ms_min: 0.081 
- point_query_1000_ms_p50: 0.116 
- point_query_1000_ms_p95: 0.219 
- point_query_1000_ms_p99: 0.258 
- point_query_1000_ms_stdev: 0.045 
- point_query_100_ms_max: 0.457 
- point_query_100_ms_mean: 0.247 
- point_query_100_ms_median: 0.234 
- point_query_100_ms_min: 0.182 
- point_query_100_ms_p50: 0.236 
- point_query_100_ms_p95: 0.348 
- point_query_100_ms_p99: 0.457 
- point_query_100_ms_stdev: 0.051 
- range_query_100000_ms_max: 0.111 
- range_query_100000_ms_mean: 0.078 
- range_query_100000_ms_median: 0.075 
- range_query_100000_ms_min: 0.069 
- range_query_100000_ms_p50: 0.076 
- range_query_100000_ms_p95: 0.091 
- range_query_100000_ms_p99: 0.111 
- range_query_100000_ms_stdev: 0.009 
- range_query_10000_ms_max: 0.129 
- range_query_10000_ms_mean: 0.092 
- range_query_10000_ms_median: 0.090 
- range_query_10000_ms_min: 0.080 
- range_query_10000_ms_p50: 0.090 
- range_query_10000_ms_p95: 0.127 
- range_query_10000_ms_p99: 0.129 
- range_query_10000_ms_stdev: 0.013 
- range_query_1000_ms_max: 0.119 
- range_query_1000_ms_mean: 0.087 
- range_query_1000_ms_median: 0.083 
- range_query_1000_ms_min: 0.076 
- range_query_1000_ms_p50: 0.083 
- range_query_1000_ms_p95: 0.109 
- range_query_1000_ms_p99: 0.119 
- range_query_1000_ms_stdev: 0.011 
- range_query_100_ms_max: 0.950 
- range_query_100_ms_mean: 0.135 
- range_query_100_ms_median: 0.105 
- range_query_100_ms_min: 0.098 
- range_query_100_ms_p50: 0.105 
- range_query_100_ms_p95: 0.134 
- range_query_100_ms_p99: 0.950 
- range_query_100_ms_stdev: 0.154 

### SQLite Write Throughput (PERF-DATABASE-003)
Status: MEASURED
Iterations: 20 (warmup: 5)
- batch_1000_individual_ms_max: 6656.928 
- batch_1000_individual_ms_mean: 5314.695 
- batch_1000_individual_ms_median: 5145.601 
- batch_1000_individual_ms_min: 5020.357 
- batch_1000_individual_ms_p50: 5146.055 
- batch_1000_individual_ms_p95: 6656.928 
- batch_1000_individual_ms_p99: 6656.928 
- batch_1000_individual_ms_stdev: 438.807 
- batch_1000_tx_ms_max: 10.796 
- batch_1000_tx_ms_mean: 6.512 
- batch_1000_tx_ms_median: 6.182 
- batch_1000_tx_ms_min: 5.536 
- batch_1000_tx_ms_p50: 6.379 
- batch_1000_tx_ms_p95: 10.796 
- batch_1000_tx_ms_p99: 10.796 
- batch_1000_tx_ms_stdev: 1.196 
- batch_100_individual_ms_max: 771.181 
- batch_100_individual_ms_mean: 551.702 
- batch_100_individual_ms_median: 507.375 
- batch_100_individual_ms_min: 442.658 
- batch_100_individual_ms_p50: 508.449 
- batch_100_individual_ms_p95: 771.181 
- batch_100_individual_ms_p99: 771.181 
- batch_100_individual_ms_stdev: 80.594 
- batch_100_tx_ms_max: 6.679 
- batch_100_tx_ms_mean: 5.164 
- batch_100_tx_ms_median: 4.994 
- batch_100_tx_ms_min: 4.552 
- batch_100_tx_ms_p50: 4.996 
- batch_100_tx_ms_p95: 6.679 
- batch_100_tx_ms_p99: 6.679 
- batch_100_tx_ms_stdev: 0.546 
- batch_10_individual_ms_max: 59.300 
- batch_10_individual_ms_mean: 51.529 
- batch_10_individual_ms_median: 51.022 
- batch_10_individual_ms_min: 43.242 
- batch_10_individual_ms_p50: 51.200 
- batch_10_individual_ms_p95: 59.300 
- batch_10_individual_ms_p99: 59.300 
- batch_10_individual_ms_stdev: 3.602 
- batch_10_tx_ms_max: 7.504 
- batch_10_tx_ms_mean: 5.239 
- batch_10_tx_ms_median: 4.954 
- batch_10_tx_ms_min: 4.555 
- batch_10_tx_ms_p50: 4.960 
- batch_10_tx_ms_p95: 7.504 
- batch_10_tx_ms_p99: 7.504 
- batch_10_tx_ms_stdev: 0.736 
- batch_1_individual_ms_max: 6.027 
- batch_1_individual_ms_mean: 4.970 
- batch_1_individual_ms_median: 4.846 
- batch_1_individual_ms_min: 4.480 
- batch_1_individual_ms_p50: 4.863 
- batch_1_individual_ms_p95: 6.027 
- batch_1_individual_ms_p99: 6.027 
- batch_1_individual_ms_stdev: 0.475 
- batch_1_tx_ms_max: 7.455 
- batch_1_tx_ms_mean: 5.440 
- batch_1_tx_ms_median: 5.052 
- batch_1_tx_ms_min: 4.417 
- batch_1_tx_ms_p50: 5.069 
- batch_1_tx_ms_p95: 7.455 
- batch_1_tx_ms_p99: 7.455 
- batch_1_tx_ms_stdev: 0.829 

### SQLite WAL Mode Performance (PERF-DATABASE-004)
Status: MEASURED
Iterations: 20 (warmup: 5)
- rollback_read_100_ms_max: 4.689 
- rollback_read_100_ms_mean: 4.293 
- rollback_read_100_ms_median: 4.254 
- rollback_read_100_ms_min: 4.145 
- rollback_read_100_ms_p50: 4.266 
- rollback_read_100_ms_p95: 4.689 
- rollback_read_100_ms_p99: 4.689 
- rollback_read_100_ms_stdev: 0.143 
- rollback_write_100_ms_max: 5.995 
- rollback_write_100_ms_mean: 4.869 
- rollback_write_100_ms_median: 4.786 
- rollback_write_100_ms_min: 4.450 
- rollback_write_100_ms_p50: 4.794 
- rollback_write_100_ms_p95: 5.995 
- rollback_write_100_ms_p99: 5.995 
- rollback_write_100_ms_stdev: 0.332 
- wal_read_100_ms_max: 0.839 
- wal_read_100_ms_mean: 0.458 
- wal_read_100_ms_median: 0.424 
- wal_read_100_ms_min: 0.410 
- wal_read_100_ms_p50: 0.425 
- wal_read_100_ms_p95: 0.839 
- wal_read_100_ms_p99: 0.839 
- wal_read_100_ms_stdev: 0.098 
- wal_write_100_ms_max: 4.993 
- wal_write_100_ms_mean: 4.585 
- wal_write_100_ms_median: 4.540 
- wal_write_100_ms_min: 4.388 
- wal_write_100_ms_p50: 4.561 
- wal_write_100_ms_p95: 4.993 
- wal_write_100_ms_p99: 4.993 
- wal_write_100_ms_stdev: 0.171 

## ipc

### IPC Serialization Overhead (PERF-IPC-003)
Status: MEASURED
Iterations: 100 (warmup: 10)
- payload_0_deserialize_ms_max: 0.018 
- payload_0_deserialize_ms_mean: 0.003 
- payload_0_deserialize_ms_median: 0.003 
- payload_0_deserialize_ms_min: 0.002 
- payload_0_deserialize_ms_p50: 0.003 
- payload_0_deserialize_ms_p95: 0.004 
- payload_0_deserialize_ms_p99: 0.018 
- payload_0_deserialize_ms_stdev: 0.002 
- payload_0_serialize_ms_max: 0.018 
- payload_0_serialize_ms_mean: 0.004 
- payload_0_serialize_ms_median: 0.004 
- payload_0_serialize_ms_min: 0.004 
- payload_0_serialize_ms_p50: 0.004 
- payload_0_serialize_ms_p95: 0.007 
- payload_0_serialize_ms_p99: 0.018 
- payload_0_serialize_ms_stdev: 0.002 
- payload_0_size_bytes_max: 1056.000 
- payload_0_size_bytes_mean: 1056.000 
- payload_0_size_bytes_median: 1056.000 
- payload_0_size_bytes_min: 1056.000 
- payload_0_size_bytes_p50: 1056.000 
- payload_0_size_bytes_p95: 1056.000 
- payload_0_size_bytes_p99: 1056.000 
- payload_0_size_bytes_stdev: 0.000 
- payload_1_deserialize_ms_max: 0.004 
- payload_1_deserialize_ms_mean: 0.002 
- payload_1_deserialize_ms_median: 0.002 
- payload_1_deserialize_ms_min: 0.002 
- payload_1_deserialize_ms_p50: 0.002 
- payload_1_deserialize_ms_p95: 0.003 
- payload_1_deserialize_ms_p99: 0.004 
- payload_1_deserialize_ms_stdev: 0.000 
- payload_1_serialize_ms_max: 0.005 
- payload_1_serialize_ms_mean: 0.002 
- payload_1_serialize_ms_median: 0.002 
- payload_1_serialize_ms_min: 0.002 
- payload_1_serialize_ms_p50: 0.002 
- payload_1_serialize_ms_p95: 0.003 
- payload_1_serialize_ms_p99: 0.005 
- payload_1_serialize_ms_stdev: 0.000 
- payload_1_size_bytes_max: 153.000 
- payload_1_size_bytes_mean: 153.000 
- payload_1_size_bytes_median: 153.000 
- payload_1_size_bytes_min: 153.000 
- payload_1_size_bytes_p50: 153.000 
- payload_1_size_bytes_p95: 153.000 
- payload_1_size_bytes_p99: 153.000 
- payload_1_size_bytes_stdev: 0.000 
- payload_2_deserialize_ms_max: 0.015 
- payload_2_deserialize_ms_mean: 0.008 
- payload_2_deserialize_ms_median: 0.007 
- payload_2_deserialize_ms_min: 0.007 
- payload_2_deserialize_ms_p50: 0.007 
- payload_2_deserialize_ms_p95: 0.012 
- payload_2_deserialize_ms_p99: 0.015 
- payload_2_deserialize_ms_stdev: 0.001 
- payload_2_serialize_ms_max: 0.029 
- payload_2_serialize_ms_mean: 0.013 
- payload_2_serialize_ms_median: 0.013 
- payload_2_serialize_ms_min: 0.013 
- payload_2_serialize_ms_p50: 0.013 
- payload_2_serialize_ms_p95: 0.021 
- payload_2_serialize_ms_p99: 0.029 
- payload_2_serialize_ms_stdev: 0.003 
- payload_2_size_bytes_max: 5373.000 
- payload_2_size_bytes_mean: 5373.000 
- payload_2_size_bytes_median: 5373.000 
- payload_2_size_bytes_min: 5373.000 
- payload_2_size_bytes_p50: 5373.000 
- payload_2_size_bytes_p95: 5373.000 
- payload_2_size_bytes_p99: 5373.000 
- payload_2_size_bytes_stdev: 0.000 
- payload_3_deserialize_ms_max: 0.048 
- payload_3_deserialize_ms_mean: 0.021 
- payload_3_deserialize_ms_median: 0.020 
- payload_3_deserialize_ms_min: 0.019 
- payload_3_deserialize_ms_p50: 0.020 
- payload_3_deserialize_ms_p95: 0.028 
- payload_3_deserialize_ms_p99: 0.048 
- payload_3_deserialize_ms_stdev: 0.004 
- payload_3_serialize_ms_max: 0.070 
- payload_3_serialize_ms_mean: 0.037 
- payload_3_serialize_ms_median: 0.034 
- payload_3_serialize_ms_min: 0.033 
- payload_3_serialize_ms_p50: 0.034 
- payload_3_serialize_ms_p95: 0.062 
- payload_3_serialize_ms_p99: 0.070 
- payload_3_serialize_ms_stdev: 0.008 
- payload_3_size_bytes_max: 11378.000 
- payload_3_size_bytes_mean: 11378.000 
- payload_3_size_bytes_median: 11378.000 
- payload_3_size_bytes_min: 11378.000 
- payload_3_size_bytes_p50: 11378.000 
- payload_3_size_bytes_p95: 11378.000 
- payload_3_size_bytes_p99: 11378.000 
- payload_3_size_bytes_stdev: 0.000 

## load

### Agent Conversation Memory Growth (PERF-MEMORY-LEAK-001)
Status: MEASURED
Iterations: 1 (warmup: 0)
- heap_growth_mb_max: 0.000 
- heap_growth_mb_mean: 0.000 
- heap_growth_mb_median: 0.000 
- heap_growth_mb_min: 0.000 
- heap_growth_mb_stdev: 0.000 
- leak_detected_max: 0.000 
- leak_detected_mean: 0.000 
- leak_detected_median: 0.000 
- leak_detected_min: 0.000 
- leak_detected_stdev: 0.000 
- object_growth_max: 0.000 
- object_growth_mean: 0.000 
- object_growth_median: 0.000 
- object_growth_min: 0.000 
- object_growth_stdev: 0.000 
- rss_growth_mb_max: 0.000 
- rss_growth_mb_mean: 0.000 
- rss_growth_mb_median: 0.000 
- rss_growth_mb_min: 0.000 
- rss_growth_mb_stdev: 0.000 
- rss_slope_max: 0.000 
- rss_slope_mean: 0.000 
- rss_slope_median: 0.000 
- rss_slope_min: 0.000 
- rss_slope_stdev: 0.000 
- severity_high_max: 0.000 
- severity_high_mean: 0.000 
- severity_high_median: 0.000 
- severity_high_min: 0.000 
- severity_high_stdev: 0.000 

## storage

### Artifact Storage Operations (PERF-STORAGE-002)
Status: MEASURED
Iterations: 10 (warmup: 2)
- hash_102400_ms_max: 0.076 
- hash_102400_ms_mean: 0.062 
- hash_102400_ms_median: 0.061 
- hash_102400_ms_min: 0.050 
- hash_102400_ms_stdev: 0.008 
- hash_10240_ms_max: 0.012 
- hash_10240_ms_mean: 0.009 
- hash_10240_ms_median: 0.009 
- hash_10240_ms_min: 0.007 
- hash_10240_ms_stdev: 0.001 
- hash_1024_ms_max: 0.017 
- hash_1024_ms_mean: 0.007 
- hash_1024_ms_median: 0.004 
- hash_1024_ms_min: 0.003 
- hash_1024_ms_stdev: 0.006 
- hash_1048576_ms_max: 0.603 
- hash_1048576_ms_mean: 0.525 
- hash_1048576_ms_median: 0.504 
- hash_1048576_ms_min: 0.480 
- hash_1048576_ms_stdev: 0.050 
- read_102400_ms_max: 12.998 
- read_102400_ms_mean: 5.830 
- read_102400_ms_median: 4.925 
- read_102400_ms_min: 3.812 
- read_102400_ms_stdev: 2.819 
- read_10240_ms_max: 28.651 
- read_10240_ms_mean: 7.261 
- read_10240_ms_median: 5.014 
- read_10240_ms_min: 3.816 
- read_10240_ms_stdev: 7.547 
- read_1024_ms_max: 7.104 
- read_1024_ms_mean: 5.300 
- read_1024_ms_median: 5.219 
- read_1024_ms_min: 4.651 
- read_1024_ms_stdev: 0.731 
- read_1048576_ms_max: 6.062 
- read_1048576_ms_mean: 5.235 
- read_1048576_ms_median: 5.199 
- read_1048576_ms_min: 4.391 
- read_1048576_ms_stdev: 0.542 
- verify_102400_ms_max: 0.085 
- verify_102400_ms_mean: 0.070 
- verify_102400_ms_median: 0.069 
- verify_102400_ms_min: 0.057 
- verify_102400_ms_stdev: 0.009 
- verify_10240_ms_max: 0.044 
- verify_10240_ms_mean: 0.022 
- verify_10240_ms_median: 0.017 
- verify_10240_ms_min: 0.015 
- verify_10240_ms_stdev: 0.009 
- verify_1024_ms_max: 0.045 
- verify_1024_ms_mean: 0.018 
- verify_1024_ms_median: 0.016 
- verify_1024_ms_min: 0.009 
- verify_1024_ms_stdev: 0.011 
- verify_1048576_ms_max: 0.620 
- verify_1048576_ms_mean: 0.562 
- verify_1048576_ms_median: 0.594 
- verify_1048576_ms_min: 0.489 
- verify_1048576_ms_stdev: 0.060 
- write_102400_ms_max: 0.823 
- write_102400_ms_mean: 0.437 
- write_102400_ms_median: 0.394 
- write_102400_ms_min: 0.371 
- write_102400_ms_stdev: 0.137 
- write_10240_ms_max: 0.602 
- write_10240_ms_mean: 0.422 
- write_10240_ms_median: 0.416 
- write_10240_ms_min: 0.294 
- write_10240_ms_stdev: 0.091 
- write_1024_ms_max: 0.734 
- write_1024_ms_mean: 0.440 
- write_1024_ms_median: 0.403 
- write_1024_ms_min: 0.309 
- write_1024_ms_stdev: 0.137 
- write_1048576_ms_max: 1.181 
- write_1048576_ms_mean: 0.897 
- write_1048576_ms_median: 0.839 
- write_1048576_ms_min: 0.643 
- write_1048576_ms_stdev: 0.216 

## web

### Desktop Bundle Size (PERF-BUNDLE-001)
Status: MEASURED
Iterations: 1 (warmup: 3)
- top_js_0_bytes_max: 3373415.000 
- top_js_0_bytes_mean: 3373415.000 
- top_js_0_bytes_median: 3373415.000 
- top_js_0_bytes_min: 3373415.000 
- top_js_0_bytes_stdev: 0.000 
- top_js_1_bytes_max: 779873.000 
- top_js_1_bytes_mean: 779873.000 
- top_js_1_bytes_median: 779873.000 
- top_js_1_bytes_min: 779873.000 
- top_js_1_bytes_stdev: 0.000 
- top_js_2_bytes_max: 779847.000 
- top_js_2_bytes_mean: 779847.000 
- top_js_2_bytes_median: 779847.000 
- top_js_2_bytes_min: 779847.000 
- top_js_2_bytes_stdev: 0.000 
- top_js_3_bytes_max: 626126.000 
- top_js_3_bytes_mean: 626126.000 
- top_js_3_bytes_median: 626126.000 
- top_js_3_bytes_min: 626126.000 
- top_js_3_bytes_stdev: 0.000 
- top_js_4_bytes_max: 626126.000 
- top_js_4_bytes_mean: 626126.000 
- top_js_4_bytes_median: 626126.000 
- top_js_4_bytes_min: 626126.000 
- top_js_4_bytes_stdev: 0.000 
- top_js_5_bytes_max: 622325.000 
- top_js_5_bytes_mean: 622325.000 
- top_js_5_bytes_median: 622325.000 
- top_js_5_bytes_min: 622325.000 
- top_js_5_bytes_stdev: 0.000 
- top_js_6_bytes_max: 622325.000 
- top_js_6_bytes_mean: 622325.000 
- top_js_6_bytes_median: 622325.000 
- top_js_6_bytes_min: 622325.000 
- top_js_6_bytes_stdev: 0.000 
- top_js_7_bytes_max: 262384.000 
- top_js_7_bytes_mean: 262384.000 
- top_js_7_bytes_median: 262384.000 
- top_js_7_bytes_min: 262384.000 
- top_js_7_bytes_stdev: 0.000 
- top_js_8_bytes_max: 262384.000 
- top_js_8_bytes_mean: 262384.000 
- top_js_8_bytes_median: 262384.000 
- top_js_8_bytes_min: 262384.000 
- top_js_8_bytes_stdev: 0.000 
- top_js_9_bytes_max: 236177.000 
- top_js_9_bytes_mean: 236177.000 
- top_js_9_bytes_median: 236177.000 
- top_js_9_bytes_min: 236177.000 
- top_js_9_bytes_stdev: 0.000 
- total_assets_bytes_max: 5094175.000 
- total_assets_bytes_mean: 5094175.000 
- total_assets_bytes_median: 5094175.000 
- total_assets_bytes_min: 5094175.000 
- total_assets_bytes_stdev: 0.000 
- total_css_bytes_max: 500625.000 
- total_css_bytes_mean: 500625.000 
- total_css_bytes_median: 500625.000 
- total_css_bytes_min: 500625.000 
- total_css_bytes_stdev: 0.000 
- total_html_bytes_max: 1248.000 
- total_html_bytes_mean: 1248.000 
- total_html_bytes_median: 1248.000 
- total_html_bytes_min: 1248.000 
- total_html_bytes_stdev: 0.000 
- total_js_bytes_max: 23608270.000 
- total_js_bytes_mean: 23608270.000 
- total_js_bytes_median: 23608270.000 
- total_js_bytes_min: 23608270.000 
- total_js_bytes_stdev: 0.000 

### Duplicate Dependencies (PERF-BUNDLE-003)
Status: MEASURED
Iterations: 1 (warmup: 3)
- duplicate_details_max: 88.000 
- duplicate_details_mean: 88.000 
- duplicate_details_median: 88.000 
- duplicate_details_min: 88.000 
- duplicate_details_stdev: 0.000 
- duplicates_count_max: 88.000 
- duplicates_count_mean: 88.000 
- duplicates_count_median: 88.000 
- duplicates_count_min: 88.000 
- duplicates_count_stdev: 0.000 
- total_packages_max: 1031.000 
- total_packages_mean: 1031.000 
- total_packages_median: 1031.000 
- total_packages_min: 1031.000 
- total_packages_stdev: 0.000 
- unique_names_max: 852.000 
- unique_names_mean: 852.000 
- unique_names_median: 852.000 
- unique_names_min: 852.000 
- unique_names_stdev: 0.000 
