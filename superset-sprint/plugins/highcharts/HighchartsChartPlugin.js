/**
 * Highcharts Visualization Plugin for Apache Superset
 * 
 * Installation:
 * 1. Place this in $SUPERSET_HOME/plugins/highcharts/
 * 2. Add to manifest.json or registration
 * 3. Restart Superset
 * 
 * Supported chart types: line, bar, column, area, pie, scatter, spline
 */

import React from 'react';
import { styled } from '@superset-ui/core';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';

// Optional modules
import More from 'highcharts/highcharts-more';
import Boost from 'highcharts/modules/boost';
import ExportData from 'highcharts/modules/export-data';
import Export from 'highcharts/modules/exporting';

if (typeof Highcharts === 'object') {
  More(Highcharts);
  Boost(Highcharts);
  ExportData(Highcharts);
  Export(Highcharts);
}

// Color palette
const COLORS = ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1'];

// Default chart options factory
function getDefaultOptions(chartType) {
  return {
    chart: {
      type: chartType,
      backgroundColor: 'transparent',
      style: { fontFamily: 'Inter, Arial, sans-serif' }
    },
    colors: COLORS,
    title: { style: { color: '#334151' } },
    xAxis: {
      labels: { style: { color: '#64748b' } },
      axisLine: { color: '#e2e8f0' },
      tickColor: '#e2e8f0'
    },
    yAxis: {
      labels: { style: { color: '#64748b' } },
      gridLineColor: '#f1f5f9'
    },
    legend: { itemStyle: { color: '#475569' } },
    tooltip: {
      backgroundColor: '#1e293b',
      borderColor: '#334155',
      style: { color: '#f8fafc' }
    },
    plotOptions: {
      series: { animation: { duration: 800 } },
      pie: { allowPointSelect: true, cursor: 'pointer' }
    },
    credits: { enabled: false }
  };
}

const StyledWrapper = styled.div`
  width: 100%;
  height: 100%;
  min-height: 400px;
`;

export default class HighchartsChartPlugin {
  constructor() {
    this.name = 'Highcharts';
    this.chartType = 'highcharts';
  }

  /** Convert Superset formData to Highcharts options */
  buildOptions(formData, payload) {
    const { 
      viz_type = 'line',
      groupby = [],
      metrics = [],
      columns = [],
      show_legend = true,
      show_labels = true
    } = formData;

    const data = payload?.data || [];
    const metricLabels = metrics.map(m => m.label || m);
    const groupbyFields = groupby.slice(0, 2); // max 2 grouping dimensions

    // Build series based on dimensions
    let series = [];
    let categories = [];

    if (groupbyFields.length > 0 && metricLabels.length > 0) {
      // Grouped data
      const grouped = {};
      data.forEach(row => {
        const key = groupbyFields.map(g => row[g]).join(' | ');
        if (!grouped[key]) grouped[key] = { name: key, data: [] };
        grouped[key].data.push([row[groupbyFields[0]], row[metricLabels[0]]]);
      });
      series = Object.values(grouped);
      categories = [...new Set(data.map(r => r[groupbyFields[0]]))];
    } else if (metricLabels.length > 0) {
      series = [{
        name: metricLabels[0],
        data: data.map(r => Number(r[metricLabels[0]]))
      }];
      categories = data.map((_, i) => String(i + 1));
    }

    const options = getDefaultOptions(viz_type);
    options.series = series;
    options.xAxis.categories = categories;
    options.legend.enabled = show_legend;
    options.plotOptions.pie.dataLabels.enabled = show_labels;
    options.title.text = formData.slice_name || formData.datasource_name || '';

    return options;
  }

  /** React component render */
  render(payload, formData) {
    const options = this.buildOptions(formData, payload);
    return (
      <StyledWrapper>
        <HighchartsReact highcharts={Highcharts} options={options} />
      </StyledWrapper>
    );
  }
}

// Registration (Superset 3.x)
export function register(registry) {
  registry.set('highcharts', HighchartsChartPlugin);
}
