<template>
  <div class="grade-distribution pa-5">
    <div v-if="!isLoading">
      <div class="d-flex justify-space-between">
        <Header1 text="Grade Distribution" class="mb-0" />
        <div>
          <v-switch
            v-if="currentUser.isAdmin"
            v-model="isDemoMode"
            color="primary"
            density="comfortable"
            hide-details
            label="Demo mode"
            :ripple="false"
          ></v-switch>
        </div>
      </div>
      <v-alert
        v-if="errorMessage"
        class="font-weight-medium my-3"
        role="alert"
        :text="errorMessage"
        type="warning"
      />
      <div v-if="gradeDistribution">
        <div
          v-if="gradeDistribution"
          class="course-header mb-1"
        >
          <span :class="{'demo-mode-blur': isDemoMode}">{{ gradeDistribution.courseName }}</span> &mdash; {{ gradeDistribution.canvasSite.term.name }}
        </div>
        <div v-html="config.newtInformationBlock"></div>
        <v-card class="container mb-4" elevation="0">
          <DemographicsChart
            :chart-defaults="chartDefaults"
            :colors="colors"
            :course-name="gradeDistribution.courseName"
            :grade-distribution="gradeDistribution.demographics"
            :is-demo-mode="isDemoMode"
          />
        </v-card>
        <v-card class="container mb-4" elevation="0">
          <PriorEnrollmentChart
            :chart-defaults="chartDefaults"
            :colors="colors"
            :course-name="gradeDistribution.courseName"
            :grade-distribution="gradeDistribution.enrollments"
            :is-demo-mode="isDemoMode"
            :terms="orderBy(gradeDistribution.terms, ['id'], ['desc'])"
          />
        </v-card>
      </div>
    </div>
  </div>
</template>

<script>
import Context from '@/mixins/Context'
import DemographicsChart from '@/components/bcourses/analytics/DemographicsChart'
import Header1 from '@/components/utils/Header1'
import PriorEnrollmentChart from '@/components/bcourses/analytics/PriorEnrollmentChart'
import {get, orderBy, size} from 'lodash'
import {getGradeDistribution} from '@/api/grade-distribution'

export default {
  name: 'CourseGradeDistribution',
  components: {
    DemographicsChart,
    Header1,
    PriorEnrollmentChart
  },
  mixins: [Context],
  data: () => ({
    chartDefaults: {
      chart: {
        backgroundColor: 'transparent',
        marginTop: 145
      },
      lang: {
        noData: 'No data available until final grades are returned.'
      },
      legend: {
        align: 'right',
        enabled: true,
        floating: true,
        itemStyle: {
          fontSize: '1em'
        },
        labelFormat: '{name}',
        layout: 'vertical',
        symbolPadding: 10,
        symbolRadius: 0,
        verticalAlign: 'top',
        y: 30
      },
      noData: {
        style: {
          fontSize: '18px',
          color: '#999'
        }
      },
      plotOptions: {
        series: {
          borderWidth: 0,
          dataLabels: {
            enabled: false
          },
          groupPadding: .1
        }
      },
      series: [
        {
          data: []
        }
      ],
      title: {
        align: 'left',
        margin: 45,
        style: {
          color: '#474747'
        },
        y: 23
      },
      tooltip: {
        shared: true,
        stickOnContact: true,
        useHTML: true
      },
      xAxis: {
        categories: [],
        labels: {
          autoRotationLimit: 0,
          overflow: 'allow',
          style: {
            color: '#999',
            fontSize: 15
          }
        },
        lineColor: '#CCC',
        lineWidth: 2,
        tickColor: '#CCC',
        tickmarkPlacement: 'on',
        tickWidth: 1
      },
      yAxis: {
        endOnTick: false,
        gridLineWidth: 0,
        labels: {
          style: {
            color: '#999',
            fontSize: 16
          }
        },
        lineColor: '#999',
        lineWidth: 1,
        tickColor: '#CCC',
        tickWidth: 1,
        title: {
          enabled: false
        }
      }
    },
    colors: {
      primary: '#8BBDDA',
      secondary: '#DAB38B',
      tertiary: '#C5E1F2',
      quaternary: '#FCCE9F'
    },
    errorMessage: undefined,
    gradeDistribution: undefined,
    isDemoMode: false
  }),
  watch: {
    isDemoMode(val) {
      if (this.currentUser.isAdmin) {
        localStorage.setItem('isDemoMode', val)
      }
    }
  },
  created() {
    this.loadingStart()
    this.isDemoMode = this.currentUser.isAdmin && localStorage.getItem('isDemoMode') === 'true'
    this.chartDefaults.series[0].color = this.colors.primary
    getGradeDistribution(this.currentUser.canvasSiteId).then(
      data => {
        this.gradeDistribution = data
      },
      error => this.showError(error)
    ).catch(error => this.showError(error)
    ).finally(() => this.$ready())
  },
  methods: {
    get,
    orderBy,
    showError(errorMessage) {
      this.errorMessage = errorMessage
    },
    size
  }
}
</script>

<!-- eslint-disable-next-line vue-scoped-css/enforce-style-type  -->
<style lang="scss">
.grade-distribution {
  .course-header {
    color: $color-nobel;
    font-size: 17px;
    font-weight: 400;
  }
  .demo-mode-blur {
    color: transparent !important;
    text-shadow: 0 0 15px rgba(0, 0, 0, 0.7) !important;
  }
  .grade-distribution-table-border {
    border-left: solid 1px $color-container-grey-border;
  }
  .pilot-notice {
    color: $color-harley-davidson-orange;
    font-size: 15px;
    font-weight: 600;
  }
  h2 {
    font-weight: 500;
  }
  hr {
    border-color: $color-grey !important;
    border-style: solid none solid none !important;
    color: $color-grey !important;
  }
  table {
    caption {
      color: $color-body-black !important;
    }
    tbody tr:hover {
      background-color: $color-table-cell-bg-grey;
    }
    th {
      vertical-align: bottom;
    }
  }
}
</style>
