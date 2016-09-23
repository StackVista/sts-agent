
require './ci/common'

namespace :ci do
  namespace :network do |flavor|
    task before_install: ['ci:common:before_install']

    task install: ['ci:common:install']

    task before_script: ['ci:common:before_script']
    # If you need to wait on a start of a progran, please use Wait.for,
    # see https://github.com/DataDog/dd-agent/pull/1547

    task script: ['ci:common:script'] do
      this_provides = [
        'network'
      ]
      Rake::Task['ci:common:run_tests'].invoke(this_provides)
    end

    task before_cache: ['ci:common:before_cache']

    task cleanup: ['ci:common:cleanup']

    task :execute do
      Rake::Task['ci:common:execute'].invoke(flavor)
    end
  end
end
